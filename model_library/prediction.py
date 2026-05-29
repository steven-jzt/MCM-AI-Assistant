"""
预测模型库 — prediction.py
===========================
包含灰色预测 GM(1,1)、ARIMA 自动定阶（含残差白噪声检验）、
指数平滑、LSTM（含 Dropout + EarlyStopping + 验证集）及评估指标、过拟合检查。
用于数学建模竞赛中的时间序列预测问题。
"""

import warnings
from typing import List, Tuple, Optional, Union

import numpy as np
import pandas as pd
from scipy import stats

# ============================================================================
# 辅助函数
# ============================================================================

def _check_input(data: Union[List, np.ndarray], min_len: int = 4,
                 name: str = "数据") -> np.ndarray:
    """统一输入校验，转为一维 float 数组。"""
    if isinstance(data, list):
        data = np.array(data, dtype=float)
    else:
        data = np.asarray(data, dtype=float)
    data = data.ravel()
    if data.shape[0] < min_len:
        raise ValueError(f"{name}长度至少需要 {min_len}，当前长度为 {data.shape[0]}")
    return data


# ============================================================================
# 1. 灰色预测 GM(1,1)
# ============================================================================

def gm11(train_data: Union[List, np.ndarray],
         predict_n: int = 1) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    灰色预测 GM(1,1) 模型。

    适用于小样本、贫信息的时间序列，核心假设是序列的 1-AGO 生成序列服从指数增长。

    Parameters
    ----------
    train_data : list or np.ndarray, shape (n,)
        原始训练序列（非负序列）。
    predict_n : int
        向后预测的步数。

    Returns
    -------
    fit_values : np.ndarray, shape (n,)
        对训练集的拟合值。
    pred_values : np.ndarray, shape (predict_n,)
        预测值。
    c_ratio : float
        后验差比值 C。C < 0.35 优，< 0.5 合格，< 0.65 勉强，>= 0.65 不合格。

    Raises
    ------
    ValueError
        若数据非正（含零或负值）或数据量小于 4。

    Notes
    -----
    - 自动进行级比检验，若不符合 $\\sigma(k) \\in (e^{-2/(n+1)}, e^{2/(n+1)})$，
      提示对原始序列做平移变换。
    - 若数据含零或负值，需先做平移变换使所有值大于 0。
    - 级比检验区间为 $\\sigma(k) \\in (e^{-2/(n+1)}, e^{2/(n+1)})$。

    References
    ----------
    Julong Deng (1989). "Introduction to Grey System Theory."

    Examples
    --------
    >>> x = [2.874, 3.278, 3.337, 3.390, 3.679]
    >>> fit, pred, c = gm11(x, predict_n=2)
    """
    x0 = _check_input(train_data, min_len=4, name="训练数据")

    if np.any(x0 <= 0):
        raise ValueError("GM(1,1) 要求数据均为正数。若含非正值，请对序列做平移变换（加常数）。")

    n = len(x0)

    # ---- 级比检验 ----
    sigma = x0[:-1] / x0[1:]
    lower = np.exp(-2.0 / (n + 1))
    upper = np.exp(2.0 / (n + 1))
    pass_test = np.all((sigma >= lower) & (sigma <= upper))
    if not pass_test:
        warnings.warn(
            f"级比检验未通过：部分级比不在 ({lower:.4f}, {upper:.4f}) 范围内。"
            f"建议对原始序列做平移变换（所有值加常数），使新序列通过检验。",
            UserWarning,
        )
    else:
        print(f"[GM(1,1)] 级比检验通过，级比范围: ({sigma.min():.4f}, {sigma.max():.4f})")

    # 1-AGO 累加生成
    x1 = np.cumsum(x0)

    # 紧邻均值生成
    z1 = 0.5 * (x1[:-1] + x1[1:])

    # 最小二乘估计参数 a (发展系数), b (灰作用量)
    B = np.column_stack([-z1, np.ones(n - 1)])
    Y = x0[1:]
    u = np.linalg.lstsq(B, Y, rcond=None)[0]
    a, b = u[0], u[1]

    # 时间响应函数
    def x1_hat(k):
        return (x0[0] - b / a) * np.exp(-a * k) + b / a

    # 拟合值（1-AGO 还原）
    total_len = n + predict_n
    x1_pred = x1_hat(np.arange(total_len))
    x0_hat = np.diff(x1_pred, prepend=x1_pred[0] - (x0[0] - x1_hat(0)) / 2)
    x0_hat[0] = x0[0]  # 第一个点还原为原始值

    fit_values = x0_hat[:n]
    pred_values = x0_hat[n:]

    # 后验差检验
    e = x0 - fit_values
    s1 = np.std(e, ddof=1)
    s2 = np.std(x0, ddof=1)
    c_ratio = s1 / s2 if s2 > 1e-10 else 0.0

    grade = "优" if c_ratio < 0.35 else ("合格" if c_ratio < 0.5 else
              ("勉强" if c_ratio < 0.65 else "不合格"))
    print(f"[GM(1,1)] 后验差比值 C = {c_ratio:.4f} ({grade})")
    if abs(a) > 1:
        warnings.warn(f"发展系数 |a| = {abs(a):.4f} > 1，模型仅适合短期预测。", UserWarning)

    return fit_values, pred_values, c_ratio


# ============================================================================
# 2. ARIMA 自动定阶
# ============================================================================

def arima_auto(
    train_data: Union[List, np.ndarray],
    predict_n: int = 1,
    max_order: Tuple[int, int, int] = (2, 1, 2),
    significance: float = 0.05,
) -> Tuple[np.ndarray, pd.DataFrame]:
    """
    ARIMA 自动定阶预测。

    依次执行 ADF 平稳性检验 → 差分确定 d → AIC 最小化搜索 (p, q) → 预测。

    Parameters
    ----------
    train_data : list or np.ndarray, shape (n,)
        原始时间序列。
    predict_n : int
        预测步数。
    max_order : tuple (p_max, d_max, q_max)
        搜索范围上限，默认 (2, 1, 2)。
    significance : float
        ADF 检验显著性水平，默认 0.05。

    Returns
    -------
    forecast : np.ndarray, shape (predict_n,)
        预测值。
    ci_df : pd.DataFrame
        包含 mean, lower, upper 三列的置信区间（95%）DataFrame。

    Raises
    ------
    ImportError
        若未安装 statsmodels。

    Notes
    -----
    - 差分阶数 d 由 ADF 检验自动确定，最多差分 d_max 次。
    - 若 d = 0 且序列仍不平稳，仍按 d=0 建模并给出警告。
    """
    try:
        from statsmodels.tsa.arima.model import ARIMA
        from statsmodels.tsa.stattools import adfuller
    except ImportError:
        raise ImportError("ARIMA 需要 statsmodels 库。请运行: pip install statsmodels")

    series = _check_input(train_data, min_len=6, name="训练数据")
    p_max, d_max, q_max = max_order

    # ---- ADF 检验确定差分阶数 d ----
    d = 0
    ts = series.copy()
    for d_candidate in range(d_max + 1):
        adf_result = adfuller(ts, autolag="AIC")
        p_value = adf_result[1]
        if p_value < significance:
            d = d_candidate
            print(f"[ARIMA] ADF 检验通过: p-value = {p_value:.4f} < {significance}, d = {d}")
            break
        print(f"[ARIMA] ADF 检验 d={d_candidate}: p-value = {p_value:.4f} >= {significance}，继续差分")
        if d_candidate < d_max:
            ts = np.diff(ts)
    else:
        d = d_max
        print(f"[ARIMA] 经 {d_max} 次差分仍未平稳，取 d = {d_max}")

    # ---- AIC 定阶搜索 (p, q) ----
    best_aic = np.inf
    best_order = (0, d, 0)
    best_model = None

    for p in range(p_max + 1):
        for q in range(q_max + 1):
            if p == 0 and q == 0:
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model = ARIMA(series, order=(p, d, q))
                    fitted = model.fit(method_kwargs={"maxiter": 200})
                if fitted.aic < best_aic:
                    best_aic = fitted.aic
                    best_order = (p, d, q)
                    best_model = fitted
            except Exception:
                continue

    if best_model is None:
        raise RuntimeError("ARIMA 模型拟合失败，请检查数据质量或放宽 max_order。")

    print(f"[ARIMA] 最优阶数: (p, d, q) = {best_order}, AIC = {best_aic:.2f}")

    # ---- 残差白噪声检验 (Ljung-Box) ----
    residuals = best_model.resid
    try:
        from statsmodels.stats.diagnostic import acorr_ljungbox
        lb_result = acorr_ljungbox(residuals, lags=[min(10, max(1, len(residuals)//5))],
                                   return_df=True)
        lb_pvalue = lb_result["lb_pvalue"].values[0] if "lb_pvalue" in lb_result.columns else lb_result.iloc[0, 1]
        if lb_pvalue < 0.05:
            warnings.warn(
                f"[残差检验警告] Ljung-Box 检验 p-value = {lb_pvalue:.4f} < 0.05，"
                f"残差不是白噪声，模型可能遗漏了数据中的模式。建议：(1) 尝试更大的 p, q；"
                f"(2) 检查是否需要季节性差分；(3) 考虑使用非线性模型（如 LSTM）。",
                UserWarning,
            )
        else:
            print(f"[ARIMA] 残差白噪声检验通过: Ljung-Box p-value = {lb_pvalue:.4f} >= 0.05")
    except Exception as e:
        lb_pvalue = None
        print(f"[ARIMA] 残差检验跳过: {e}")

    # ---- 预测 ----
    result = best_model.get_forecast(steps=predict_n)
    forecast = result.predicted_mean
    ci = result.conf_int(alpha=0.05)

    ci_df = pd.DataFrame({
        "mean": forecast,
        "lower": ci[:, 0],
        "upper": ci[:, 1],
    })

    return forecast, ci_df, best_order


# ============================================================================
# 3. 指数平滑法（Holt-Winters 简化版）
# ============================================================================

def exponential_smoothing(
    train_data: Union[List, np.ndarray],
    predict_n: int = 1,
    trend: Optional[str] = None,
    seasonal: Optional[int] = None,
    seasonal_type: str = "additive",
) -> Tuple[np.ndarray, pd.DataFrame]:
    """
    指数平滑法预测（基于 statsmodels）。

    自动优化平滑参数，支持无趋势/加性趋势/乘性趋势及季节分量。

    Parameters
    ----------
    train_data : list or np.ndarray
        原始时间序列。
    predict_n : int
        预测步数。
    trend : str, optional
        趋势类型：None (简单平滑), "add" (加性趋势), "mul" (乘性趋势)。
        默认 None 时根据数据自动判断（若有漂移则用 add）。
    seasonal : int, optional
        季节周期长度（如 12 表示月度数据的年周期）。None 表示不考虑季节性。
    seasonal_type : str
        "additive" 或 "multiplicative"，默认加法。

    Returns
    -------
    forecast : np.ndarray, shape (predict_n,)
        预测值。
    result_df : pd.DataFrame
        包含 mean, fitted 的 DataFrame。

    Raises
    ------
    ImportError
        若未安装 statsmodels。

    Examples
    --------
    >>> x = [10, 12, 13, 15, 18, 20]
    >>> fcst, _ = exponential_smoothing(x, predict_n=3, trend="add")
    """
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
    except ImportError:
        raise ImportError("指数平滑需要 statsmodels 库。请运行: pip install statsmodels")

    series = _check_input(train_data, min_len=4, name="训练数据")

    # 构建并拟合模型
    kwargs = {}
    if seasonal is not None and seasonal > 1 and len(series) >= 2 * seasonal:
        trend_val = trend if trend else "add"
        model = ExponentialSmoothing(
            series,
            trend=trend_val,
            seasonal=seasonal_type,
            seasonal_periods=seasonal,
            initialization_method="estimated",
        )
    else:
        trend_val = trend if trend else "add"
        model = ExponentialSmoothing(
            series,
            trend=trend_val,
            initialization_method="estimated",
        )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fitted = model.fit()

    # 预测
    forecast = fitted.forecast(predict_n)
    fitted_values = fitted.fittedvalues

    result_df = pd.DataFrame({
        "mean": np.concatenate([fitted_values, forecast]),
        "fitted": fitted_values,
    })

    return forecast, result_df


# ============================================================================
# 4. LSTM 预测（可选依赖）
# ============================================================================

def lstm_predict(
    train_data: Union[List, np.ndarray],
    predict_n: int = 1,
    look_back: int = 3,
    epochs: int = 100,
    validation_split: float = 0.2,
    dropout: float = 0.2,
    patience: int = 10,
    verbose: int = 0,
) -> dict:
    """
    基于 LSTM 的时间序列预测（含防过拟合机制）。

    使用滑动窗口将时间序列转化为监督学习样本，训练 LSTM 网络进行多步预测。
    内置 Dropout 层、验证集划分、EarlyStopping 防止过拟合。

    Parameters
    ----------
    train_data : list or np.ndarray
        原始一维时间序列。
    predict_n : int
        预测步数。
    look_back : int
        用过去多少步预测下一步，即滑动窗口大小。
    epochs : int
        最大训练轮数。
    validation_split : float
        验证集比例，默认 0.2。设置为 0 则跳过验证集监控。
    dropout : float
        Dropout 比例，默认 0.2。
    patience : int
        EarlyStopping 耐心值（验证 loss 不下降时等待的 epoch 数）。
    verbose : int
        Keras 训练日志级别，0 为静默。

    Returns
    -------
    result : dict
        keys:
        - predictions : np.ndarray — 预测值
        - history : dict — 训练历史 (loss, val_loss)
        - train_loss : float — 最终训练 loss
        - val_loss : float or None — 最终验证 loss
        - stopped_early : bool — 是否被 EarlyStopping 提前终止
        - epochs_run : int — 实际训练轮数

    Notes
    -----
    - 需要 tensorflow 库：`pip install tensorflow`
    - 数据较少时效果不佳，建议 n > 50 时使用。
    - 迭代式预测：每预测一步，将其加入序列，再预测下一步。
    - 训练/验证 loss 对比可辅助判断过拟合：若 val_loss >> train_loss，需增大 dropout 或减小 look_back。

    Examples
    --------
    >>> import numpy as np
    >>> x = np.sin(np.linspace(0, 4 * np.pi, 100))
    >>> res = lstm_predict(x, predict_n=5, look_back=5, epochs=60)
    >>> print(f"预测值: {res['predictions']}, Epochs: {res['epochs_run']}")
    """
    try:
        import tensorflow as tf
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout
        from tensorflow.keras.callbacks import EarlyStopping
    except ImportError:
        raise ImportError(
            "LSTM 预测需要 TensorFlow。请运行: pip install tensorflow\n"
            "若不想安装，可跳过 LSTM，使用 ARIMA 或 GM(1,1) 替代。"
        )

    series = _check_input(train_data, min_len=look_back + 5, name="训练数据")
    n = len(series)

    # Min-max 归一化
    v_min, v_max = series.min(), series.max()
    denom = v_max - v_min if v_max > v_min else 1.0
    scaled = (series - v_min) / denom

    # 构建监督学习样本
    X, y = [], []
    for i in range(n - look_back):
        X.append(scaled[i : i + look_back])
        y.append(scaled[i + look_back])

    X_arr = np.array(X).reshape(-1, look_back, 1)
    y_arr = np.array(y)

    if len(X_arr) < 5:
        raise ValueError(f"样本数不足：序列长度 {n}，look_back {look_back}，生成仅 {len(X_arr)} 个训练样本。")

    # 构建 LSTM 模型（含 Dropout）
    model = Sequential([
        LSTM(32, activation="relu", input_shape=(look_back, 1),
             dropout=dropout, recurrent_dropout=0.0),
        Dropout(dropout),
        Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse")

    # EarlyStopping 监控 val_loss（若设置了验证集）；否则监控 train loss
    if validation_split > 0 and len(X_arr) >= 10:
        monitor = "val_loss"
        es = EarlyStopping(monitor=monitor, patience=patience,
                           restore_best_weights=True, verbose=0)
        history = model.fit(
            X_arr, y_arr,
            epochs=epochs,
            batch_size=min(16, len(X_arr)),
            validation_split=validation_split,
            verbose=verbose,
            callbacks=[es],
            shuffle=False,
        )
        val_loss = history.history["val_loss"][-1]
    else:
        monitor = "loss"
        es = EarlyStopping(monitor=monitor, patience=max(3, patience // 2),
                           restore_best_weights=True, verbose=0)
        history = model.fit(
            X_arr, y_arr,
            epochs=epochs,
            batch_size=min(16, len(X_arr)),
            verbose=verbose,
            callbacks=[es],
            shuffle=False,
        )
        val_loss = None
        if len(X_arr) < 10:
            print("[LSTM] 样本数不足 10，跳过验证集监控。")

    epochs_run = len(history.history["loss"])
    stopped_early = epochs_run < epochs
    train_loss = history.history["loss"][-1]

    if stopped_early and monitor == "val_loss":
        print(f"[LSTM] EarlyStopping 在第 {epochs_run}/{epochs} 轮触发, "
              f"train_loss={train_loss:.6f}, val_loss={val_loss:.6f}")
    elif stopped_early:
        print(f"[LSTM] EarlyStopping 在第 {epochs_run}/{epochs} 轮触发")

    # 过拟合检查
    if val_loss is not None and train_loss > 1e-10:
        ratio = val_loss / train_loss
        if ratio > 2.0:
            warnings.warn(
                f"[LSTM 过拟合警告] val_loss({val_loss:.6f}) / train_loss({train_loss:.6f}) "
                f"= {ratio:.2f} > 2.0。建议: (1) 增大 dropout (当前 {dropout}); "
                f"(2) 减小 look_back (当前 {look_back}); (3) 收集更多数据。",
                UserWarning,
            )

    # 迭代多步预测
    last_window = scaled[-look_back:].tolist()
    predictions_scaled = []

    for _ in range(predict_n):
        inp = np.array(last_window[-look_back:]).reshape(1, look_back, 1)
        pred = model.predict(inp, verbose=0)[0, 0]
        predictions_scaled.append(pred)
        last_window.append(pred)

    predictions = np.array(predictions_scaled) * denom + v_min

    return {
        "predictions": predictions,
        "history": {k: v for k, v in history.history.items()},
        "train_loss": train_loss,
        "val_loss": val_loss,
        "stopped_early": stopped_early,
        "epochs_run": epochs_run,
    }


# ============================================================================
# 5. 评估指标
# ============================================================================

def evaluate_model(actual: Union[List, np.ndarray],
                   predicted: Union[List, np.ndarray]) -> dict:
    """
    计算预测模型的常用评估指标。

    Parameters
    ----------
    actual : list or np.ndarray
        真实值。
    predicted : list or np.ndarray
        预测值。

    Returns
    -------
    metrics : dict
        包含以下键值：
        - RMSE : 均方根误差
        - MAE  : 平均绝对误差
        - MAPE : 平均绝对百分比误差 (%)
        - R2   : 决定系数
        - MAE  : 平均绝对误差
        - SMAPE: 对称平均绝对百分比误差 (%)（处理接近零的真实值更稳定）

    Examples
    --------
    >>> evaluate_model([1, 2, 3], [1.1, 2.0, 3.2])
    {'RMSE': 0.12..., 'MAE': 0.10..., 'MAPE': 4.9..., 'R2': 0.98..., 'SMAPE': 5.0...}
    """
    y_true = np.asarray(actual, dtype=float).ravel()
    y_pred = np.asarray(predicted, dtype=float).ravel()

    if len(y_true) != len(y_pred):
        raise ValueError(f"长度不一致: actual={len(y_true)}, predicted={len(y_pred)}")

    n = len(y_true)
    residuals = y_true - y_pred

    rmse = np.sqrt(np.mean(residuals ** 2))
    mae = np.mean(np.abs(residuals))

    # MAPE（处理零值）
    nonzero = y_true != 0
    if np.any(nonzero):
        mape = np.mean(np.abs(residuals[nonzero] / y_true[nonzero])) * 100
    else:
        mape = np.nan

    # SMAPE
    denom = np.abs(y_true) + np.abs(y_pred)
    denom[denom == 0] = 1e-10
    smape = np.mean(2 * np.abs(residuals) / denom) * 100

    # R²
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 1e-10 else np.nan

    return {
        "RMSE": rmse,
        "MAE": mae,
        "MAPE (%)": mape,
        "SMAPE (%)": smape,
        "R2": r2,
    }


# ============================================================================
# 6. 过拟合检查（通用）
# ============================================================================

def check_overfit(
    train_metrics: dict,
    test_metrics: dict,
    threshold: float = 2.0,
    metric_keys: tuple = ("RMSE", "MAE", "R2"),
) -> dict:
    """
    通用过拟合诊断：对比训练集和测试集的误差指标。

    若测试误差是训练误差的 threshold 倍以上，发出过拟合警告。

    Parameters
    ----------
    train_metrics : dict
        训练集指标，由 evaluate_model() 返回。
    test_metrics : dict
        测试集（或交叉验证）指标。
    threshold : float
        过拟合阈值。当 test_error / train_error > threshold 时触发警告。
        默认 2.0（测试误差超过训练误差 2 倍）。
    metric_keys : tuple
        用于比较的指标键名，默认 ("RMSE", "MAE", "R2")。
        R2 的比较方向相反。

    Returns
    -------
    result : dict
        keys:
        - overfit : bool — 是否存在过拟合
        - warnings : list[str] — 具体警告信息
        - ratios : dict — 各指标的 test/train 比值

    Notes
    -----
    - 对于误差类指标（RMSE, MAE, MAPE），ratio = test / train， > threshold 则警告。
    - 对于 R2，ratio = train / test（R2 越高越好，降低意味着过拟合）。
    - 如果差异过大，会主动打印对比表和警告信息。

    Examples
    --------
    >>> train_metrics = evaluate_model(y_train, y_train_pred)
    >>> test_metrics = evaluate_model(y_test, y_test_pred)
    >>> res = check_overfit(train_metrics, test_metrics)
    >>> if res["overfit"]:
    ...     print("模型存在过拟合风险！")
    """
    ratios = {}
    warnings_list = []
    overfit = False

    for key in metric_keys:
        if key not in train_metrics or key not in test_metrics:
            continue
        train_val = train_metrics[key]
        test_val = test_metrics[key]
        if train_val is None or test_val is None or np.isnan(train_val) or np.isnan(test_val):
            continue

        if key == "R2":
            if train_val > 1e-6:
                ratio = train_val / max(test_val, 1e-6)
            else:
                ratio = 1.0
        else:
            if train_val > 1e-6:
                ratio = test_val / train_val
            else:
                ratio = 1.0 if test_val < 1e-6 else float("inf")

        ratios[key] = ratio

        if ratio > threshold:
            overfit = True
            if key == "R2":
                msg = (f"[过拟合警告] {key}: 训练集={train_val:.4f}, "
                       f"测试集={test_val:.4f}, 比值={ratio:.2f} > {threshold}。"
                       f"训练集 R^2 显著高于测试集，可能存在过拟合。")
            else:
                msg = (f"[过拟合警告] {key}: 训练集={train_val:.4f}, "
                       f"测试集={test_val:.4f}, 比值={ratio:.2f} > {threshold}。"
                       f"测试误差是训练误差的 {ratio:.1f} 倍，可能存在过拟合。")
            warnings_list.append(msg)
            warnings.warn(msg, UserWarning)

    if not overfit:
        print("[过拟合检查] 通过：训练集与测试集误差指标在合理范围内。")

    # 打印对比表
    print(f"\n{'指标':<12} {'训练集':>10} {'测试集':>10} {'比值':>10} {'状态':>8}")
    print("-" * 52)
    for key in metric_keys:
        if key in train_metrics and key in test_metrics:
            tv = train_metrics[key]
            ttv = test_metrics[key]
            r = ratios.get(key, 1.0)
            if tv is not None and ttv is not None and not (np.isnan(tv) or np.isnan(ttv)):
                status = "!! 警告" if r > threshold else "OK 正常"
                print(f"{key:<12} {tv:>10.4f} {ttv:>10.4f} {r:>10.2f} {status:>8}")

    return {
        "overfit": overfit,
        "warnings": warnings_list,
        "ratios": ratios,
    }


# ============================================================================
# 测试示例
# ============================================================================

if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 支持中文显示（Windows 用 SimHei, macOS 用 Songti SC）
    plt.rcParams["font.sans-serif"] = ["SimHei", "Songti SC", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    np.set_printoptions(precision=4, suppress=True)
    warnings.filterwarnings("ignore")

    print("=" * 60)
    print("预测模型库 — 测试示例")
    print("=" * 60)

    # ---- 生成模拟数据 ----
    # 趋势 + 周期 + 噪声
    t = np.arange(1, 31)
    trend = 0.3 * t
    season = 2 * np.sin(2 * np.pi * t / 12)
    noise = np.random.default_rng(42).normal(0, 0.3, len(t))
    series = trend + season + noise
    series = series - series.min() + 1  # 确保正值

    train = series[:24]
    test = series[24:]
    predict_steps = len(test)

    print(f"\n训练集长度: {len(train)}, 测试集长度: {len(test)}")

    # ======== 1. GM(1,1) ========
    print("\n" + "-" * 40)
    print("[1] 灰色预测 GM(1,1)")
    print("-" * 40)
    try:
        fit_gm, pred_gm, C = gm11(train, predict_n=predict_steps)
        metrics_gm = evaluate_model(test, pred_gm)
        print(f"  预测值: {pred_gm}")
        print(f"  评估: RMSE={metrics_gm['RMSE']:.4f}, MAE={metrics_gm['MAE']:.4f}")
    except Exception as e:
        print(f"  GM(1,1) 失败: {e}")

    # ======== 2. ARIMA ========
    print("\n" + "-" * 40)
    print("[2] ARIMA 自动定阶")
    print("-" * 40)
    try:
        from statsmodels.tsa.arima.model import ARIMA
        from statsmodels.tsa.stattools import adfuller

        pred_arima, ci_df, order = arima_auto(train, predict_n=predict_steps,
                                              max_order=(3, 2, 3))
        metrics_arima = evaluate_model(test, pred_arima)
        print(f"  最优阶数: {order}")
        print(f"  预测值: {pred_arima}")
        print(f"  95% CI: [{ci_df['lower'].values}, {ci_df['upper'].values}]")
        print(f"  评估: RMSE={metrics_arima['RMSE']:.4f}, MAE={metrics_arima['MAE']:.4f}")
    except ImportError:
        print("  [跳过] 未安装 statsmodels，请 pip install statsmodels")
    except Exception as e:
        print(f"  ARIMA 失败: {e}")

    # ======== 3. 指数平滑 ========
    print("\n" + "-" * 40)
    print("[3] 指数平滑法")
    print("-" * 40)
    try:
        pred_es, df_es = exponential_smoothing(train, predict_n=predict_steps, trend="add")
        metrics_es = evaluate_model(test, pred_es)
        print(f"  预测值: {pred_es}")
        print(f"  评估: RMSE={metrics_es['RMSE']:.4f}, MAE={metrics_es['MAE']:.4f}")
    except ImportError:
        print("  [跳过] 未安装 statsmodels，请 pip install statsmodels")
    except Exception as e:
        print(f"  指数平滑失败: {e}")

    # ======== 4. LSTM（可选） ========
    print("\n" + "-" * 40)
    print("[4] LSTM 预测（可选，含 Dropout + EarlyStopping）")
    print("-" * 40)
    try:
        res_lstm = lstm_predict(train, predict_n=predict_steps, look_back=5,
                                epochs=80, validation_split=0.2, dropout=0.2, verbose=0)
        pred_lstm = res_lstm["predictions"]
        metrics_lstm = evaluate_model(test, pred_lstm)
        print(f"  预测值: {pred_lstm}")
        print(f"  训练 loss: {res_lstm['train_loss']:.6f}, "
              f"验证 loss: {res_lstm.get('val_loss', 'N/A')}")
        print(f"  Epochs: {res_lstm['epochs_run']}, 提前停止: {res_lstm['stopped_early']}")
        print(f"  评估: RMSE={metrics_lstm['RMSE']:.4f}, MAE={metrics_lstm['MAE']:.4f}")
    except ImportError:
        print("  [跳过] 未安装 TensorFlow（可选依赖），已跳过 LSTM")
    except Exception as e:
        print(f"  LSTM 失败: {e}")

    # ======== 5. 模型对比 ========
    print("\n" + "=" * 60)
    print("模型评估指标对比 (测试集)")
    print("=" * 60)
    print(f"{'模型':<14} {'RMSE':>8} {'MAE':>8} {'MAPE(%)':>10} {'R2':>8}")
    print("-" * 50)

    def print_row(name, m):
        if m is None:
            return
        print(f"{name:<14} {m['RMSE']:>8.4f} {m['MAE']:>8.4f} "
              f"{m['MAPE (%)']:>10.2f} {m['R2']:>8.4f}")

    print_row("GM(1,1)", metrics_gm if 'metrics_gm' in dir() else None)
    print_row("ARIMA", metrics_arima if 'metrics_arima' in dir() else None)
    print_row("指数平滑", metrics_es if 'metrics_es' in dir() else None)
    print_row("LSTM", metrics_lstm if 'metrics_lstm' in dir() else None)

    # ======== 6. 绘图 ========
    print("\n[绘图] 保存预测对比图至 figures/prediction_comparison.png")

    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    # 上图：各模型预测 vs 真实值
    ax = axes[0]
    ax.plot(t, series, "ko-", markersize=4, label="原始序列", zorder=5)
    ax.axvline(x=24.5, color="gray", linestyle="--", alpha=0.7, label="训练/测试分界")

    colors = {"GM(1,1)": "red", "ARIMA": "blue", "指数平滑": "green", "LSTM": "orange"}
    preds = {}
    if 'pred_gm' in dir():
        preds["GM(1,1)"] = pred_gm
    if 'pred_arima' in dir():
        preds["ARIMA"] = pred_arima
    if 'pred_es' in dir():
        preds["指数平滑"] = pred_es
    if 'pred_lstm' in dir():
        preds["LSTM"] = pred_lstm

    t_pred = np.arange(25, 25 + predict_steps)
    for name, pred_vals in preds.items():
        ax.plot(t_pred, pred_vals, "s--", color=colors[name], label=f"{name} 预测")

    ax.set_xlabel("时间 t")
    ax.set_ylabel("值")
    ax.set_title("各模型预测结果对比")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 下图：残差对比
    ax2 = axes[1]
    bar_width = 0.2
    x_pos = np.arange(predict_steps)
    for i, (name, pred_vals) in enumerate(preds.items()):
        offset = (i - len(preds) / 2 + 0.5) * bar_width
        ax2.bar(x_pos + offset, test - pred_vals, bar_width,
                color=colors[name], alpha=0.7, label=name)
    ax2.axhline(y=0, color="black", linewidth=0.8)
    ax2.set_xlabel("测试样本序号")
    ax2.set_ylabel("残差 (真实值 - 预测值)")
    ax2.set_title("各模型预测残差对比")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(x_pos)

    plt.tight_layout()
    import os
    os.makedirs("../figures", exist_ok=True)
    plt.savefig("../figures/prediction_comparison.png", dpi=150)
    plt.close()
    print("  已保存至 figures/prediction_comparison.png")

    print("\n" + "=" * 60)
    print("测试完成。")
    print("=" * 60)
