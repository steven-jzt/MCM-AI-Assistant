"""
统计分析模块 — statistics.py
=============================
包含多元回归（+VIF诊断）、岭回归/Lasso（正则化）、主成分分析、
K-means 聚类、层次聚类、相关性热力图、过拟合检查。
用于数学建模竞赛中的数据探索、降维、分类与建模分析。
"""

import warnings
from typing import Tuple, Optional, List, Union

import numpy as np
import pandas as pd


# ============================================================================
# 通用：中文绘图设置
# ============================================================================

def _set_chinese_font():
    """自动配置 matplotlib 中文字体。"""
    import matplotlib.pyplot as plt
    for font in ["SimHei", "Songti SC", "Microsoft YaHei", "WenQuanYi Micro Hei", "DejaVu Sans"]:
        try:
            plt.rcParams["font.sans-serif"] = [font]
            plt.rcParams["axes.unicode_minus"] = False
            return
        except Exception:
            continue


# ============================================================================
# 1. 多元线性回归
# ============================================================================

def multiple_regression(
    X: Union[np.ndarray, pd.DataFrame],
    y: Union[np.ndarray, pd.Series],
    standardize: bool = True,
) -> dict:
    """
    多元线性回归分析。

    基于 statsmodels OLS 进行回归，输出系数、显著性检验、VIF 共线性诊断。

    Parameters
    ----------
    X : np.ndarray shape (n, p) or pd.DataFrame
        自变量矩阵。
    y : np.ndarray shape (n,) or pd.Series
        因变量。
    standardize : bool
        是否对变量做标准化（使得系数可比），默认 True。

    Returns
    -------
    result : dict
        keys:
        - coef : 回归系数（含截距）
        - p_values : 各变量 p 值
        - r_squared : R^2 决定系数
        - adj_r_squared : 调整 R^2
        - f_stat : F 统计量
        - f_pvalue : F 检验 p 值
        - vif : 方差膨胀因子 DataFrame（多重共线性诊断，VIF > 10 表示严重共线）
        - summary : statsmodels 回归摘要对象

    Raises
    ------
    ImportError
        若未安装 statsmodels。

    Notes
    -----
    - 适用场景：分析多个自变量对因变量的影响方向与强度。
    - 若 VIF > 10，建议删除对应变量或使用岭回归。

    Examples
    --------
    >>> from sklearn.datasets import make_regression
    >>> X, y = make_regression(n_samples=100, n_features=3, noise=10, random_state=0)
    >>> res = multiple_regression(X, y)
    >>> print(f"R^2 = {res['r_squared']:.4f}")
    """
    try:
        import statsmodels.api as sm
        from statsmodels.stats.outliers_influence import variance_inflation_factor
    except ImportError:
        raise ImportError("回归分析需要 statsmodels。请运行: pip install statsmodels")

    X_arr = np.asarray(X, dtype=float)
    y_arr = np.asarray(y, dtype=float).ravel()
    n, p = X_arr.shape

    if X_arr.shape[0] != len(y_arr):
        raise ValueError(f"样本数不一致: X={X_arr.shape[0]}, y={len(y_arr)}")

    # 标准化
    if standardize:
        X_mean = X_arr.mean(axis=0)
        X_std = X_arr.std(axis=0, ddof=1)
        X_std[X_std == 0] = 1.0
        X_arr = (X_arr - X_mean) / X_std

        y_mean = y_arr.mean()
        y_std = y_arr.std(ddof=1) or 1.0
        y_arr = (y_arr - y_mean) / y_std

    # 添加截距项
    X_const = sm.add_constant(X_arr)

    # OLS 拟合
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = sm.OLS(y_arr, X_const)
        fitted = model.fit()

    # VIF 计算（排除截距项）
    vif_values = []
    for i in range(1, X_const.shape[1]):
        vif_values.append(variance_inflation_factor(X_const, i))
    vif_data = {"变量": ["截距"] + [f"X{i+1}" for i in range(p)],
                "VIF": [np.nan] + vif_values}
    vif_df = pd.DataFrame(vif_data)

    # VIF > 10 自动警告
    high_vif = [f"X{i+1}" for i, v in enumerate(vif_values) if v > 10]
    if high_vif:
        msg = (
            f"[多重共线性警告] 变量 {high_vif} 的 VIF > 10，存在严重多重共线性。\n"
            f"  建议方案：(1) 删除 VIF>10 的变量后重新拟合；\n"
            f"            (2) 调用 ridge_regression(X, y) 进行岭回归；\n"
            f"            (3) 调用 lasso_regression(X, y) 进行 Lasso 回归（可自动变量选择）。"
        )
        warnings.warn(msg, UserWarning)

    return {
        "coef": fitted.params,
        "p_values": fitted.pvalues,
        "r_squared": fitted.rsquared,
        "adj_r_squared": fitted.rsquared_adj,
        "f_stat": fitted.fvalue,
        "f_pvalue": fitted.f_pvalue,
        "vif": vif_df,
        "high_vif": high_vif,
        "summary": fitted,
    }


# ============================================================================
# 2. 岭回归（Ridge Regression）
# ============================================================================

def ridge_regression(
    X: Union[np.ndarray, pd.DataFrame],
    y: Union[np.ndarray, pd.Series],
    alpha: Optional[float] = None,
    cv: int = 5,
    standardize: bool = True,
) -> dict:
    """
    岭回归（L2 正则化），自动处理多重共线性。

    当多元回归中 VIF > 10 时推荐使用。通过交叉验证自动选取最优正则化参数 alpha。

    Parameters
    ----------
    X : np.ndarray (n, p) or pd.DataFrame
        自变量矩阵。
    y : np.ndarray (n,) or pd.Series
        因变量。
    alpha : float, optional
        正则化强度。None 时通过 RidgeCV 自动搜索最优 alpha。
    cv : int
        交叉验证折数，默认 5。
    standardize : bool
        是否先标准化，默认 True。

    Returns
    -------
    result : dict
        keys:
        - coef : 回归系数（含截距）
        - intercept : 截距
        - alpha : 使用的正则化参数
        - cv_scores : 交叉验证得分 (R^2)
        - train_r2 : 训练集 R^2
        - cv_mean_r2 : 交叉验证平均 R^2
        - overfit_ratio : 过拟合比率 (train_r2 / cv_mean_r2)
        - model : 训练好的 Ridge 对象

    Notes
    -----
    - 岭回归通过 L2 惩罚项 $\\alpha\\sum\\beta_j^2$ 收缩系数，适合处理共线性。
    - 不产生稀疏解（不将系数压缩到零），所有变量都会被保留。
    - 若需要自动变量选择（稀疏解），请使用 lasso_regression()。

    Examples
    --------
    >>> from sklearn.datasets import make_regression
    >>> X, y = make_regression(n_samples=100, n_features=5, noise=10, random_state=0)
    >>> res = ridge_regression(X, y)
    >>> print(f"最优 alpha = {res['alpha']:.4f}")
    """
    from sklearn.linear_model import RidgeCV, Ridge
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler

    X_arr = np.asarray(X, dtype=float)
    y_arr = np.asarray(y, dtype=float).ravel()
    n, p = X_arr.shape

    if X_arr.shape[0] != len(y_arr):
        raise ValueError(f"样本数不一致: X={X_arr.shape[0]}, y={len(y_arr)}")

    # 标准化
    if standardize:
        scaler_X = StandardScaler()
        X_arr = scaler_X.fit_transform(X_arr)
        scaler_y = StandardScaler()
        y_arr = scaler_y.fit_transform(y_arr.reshape(-1, 1)).ravel()

    # 自动搜索 alpha
    if alpha is None:
        alpha_grid = np.logspace(-3, 4, 50)
        ridge_cv = RidgeCV(alphas=alpha_grid, cv=cv, scoring="r2")
        ridge_cv.fit(X_arr, y_arr)
        alpha = ridge_cv.alpha_
        cv_scores = cross_val_score(Ridge(alpha=alpha), X_arr, y_arr, cv=cv, scoring="r2")
    else:
        cv_scores = cross_val_score(Ridge(alpha=alpha), X_arr, y_arr, cv=cv, scoring="r2")

    # 最终拟合
    model = Ridge(alpha=alpha)
    model.fit(X_arr, y_arr)

    train_r2 = model.score(X_arr, y_arr)
    cv_mean_r2 = cv_scores.mean()
    overfit_ratio = train_r2 / cv_mean_r2 if cv_mean_r2 > 1e-6 else float("inf")

    # 过拟合检查
    if overfit_ratio > 1.5:
        warnings.warn(
            f"[过拟合警告] 训练 R^2={train_r2:.4f}, 交叉验证 R^2={cv_mean_r2:.4f}, "
            f"比值={overfit_ratio:.2f} > 1.5。建议增大 alpha 或减少特征。",
            UserWarning,
        )

    print(f"[岭回归] alpha={alpha:.4f}, 训练 R^2={train_r2:.4f}, "
          f"{cv}折 CV 平均 R^2={cv_mean_r2:.4f} (std={cv_scores.std():.4f})")

    return {
        "coef": np.concatenate([[model.intercept_], model.coef_]),
        "intercept": model.intercept_,
        "alpha": alpha,
        "cv_scores": cv_scores,
        "train_r2": train_r2,
        "cv_mean_r2": cv_mean_r2,
        "overfit_ratio": overfit_ratio,
        "model": model,
    }


# ============================================================================
# 3. Lasso 回归（Lasso Regression）
# ============================================================================

def lasso_regression(
    X: Union[np.ndarray, pd.DataFrame],
    y: Union[np.ndarray, pd.Series],
    alpha: Optional[float] = None,
    cv: int = 5,
    max_iter: int = 5000,
    standardize: bool = True,
) -> dict:
    """
    Lasso 回归（L1 正则化），可自动变量选择。

    当多元回归中 VIF > 10 且希望产生稀疏解（剔除无关变量）时推荐使用。

    Parameters
    ----------
    X : np.ndarray (n, p) or pd.DataFrame
        自变量矩阵。
    y : np.ndarray (n,) or pd.Series
        因变量。
    alpha : float, optional
        正则化强度。None 时通过 LassoCV 自动搜索最优 alpha（使用 AIC 准则）。
    cv : int
        交叉验证折数，默认 5。
    max_iter : int
        优化最大迭代次数。
    standardize : bool
        是否先标准化。

    Returns
    -------
    result : dict
        keys:
        - coef : 回归系数（含截距，被剔除变量的系数为 0）
        - intercept : 截距
        - alpha : 使用的正则化参数
        - selected_features : 被保留的非零系数变量索引列表
        - dropped_features : 被剔除（系数为 0）的变量索引列表
        - cv_scores : 交叉验证得分 (R^2)
        - train_r2 : 训练集 R^2
        - cv_mean_r2 : 交叉验证平均 R^2
        - overfit_ratio : 过拟合比率
        - model : 训练好的 Lasso 对象

    Notes
    -----
    - Lasso 通过 L1 惩罚项 $\\alpha\\sum|\\beta_j|$ 将部分系数压缩到 0。
    - 适合高维数据或需要变量筛选的场景。
    - 若所有系数被压缩为 0，尝试减小 alpha 或换用 ridge_regression()。

    Examples
    --------
    >>> from sklearn.datasets import make_regression
    >>> X, y = make_regression(n_samples=100, n_features=20, n_informative=5, noise=5, random_state=0)
    >>> res = lasso_regression(X, y)
    >>> print(f"保留 {len(res['selected_features'])} 个变量, 剔除 {len(res['dropped_features'])} 个")
    """
    from sklearn.linear_model import LassoCV, Lasso
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler

    X_arr = np.asarray(X, dtype=float)
    y_arr = np.asarray(y, dtype=float).ravel()
    n, p = X_arr.shape

    if X_arr.shape[0] != len(y_arr):
        raise ValueError(f"样本数不一致: X={X_arr.shape[0]}, y={len(y_arr)}")

    if standardize:
        scaler_X = StandardScaler()
        X_arr = scaler_X.fit_transform(X_arr)
        scaler_y = StandardScaler()
        y_arr = scaler_y.fit_transform(y_arr.reshape(-1, 1)).ravel()

    # 自动搜索 alpha
    if alpha is None:
        alpha_grid = np.logspace(-4, 2, 100)
        lasso_cv = LassoCV(alphas=alpha_grid, cv=cv, max_iter=max_iter, random_state=0)
        lasso_cv.fit(X_arr, y_arr)
        alpha = lasso_cv.alpha_
        cv_scores = cross_val_score(Lasso(alpha=alpha, max_iter=max_iter),
                                    X_arr, y_arr, cv=cv, scoring="r2")
    else:
        cv_scores = cross_val_score(Lasso(alpha=alpha, max_iter=max_iter),
                                    X_arr, y_arr, cv=cv, scoring="r2")

    # 最终拟合
    model = Lasso(alpha=alpha, max_iter=max_iter)
    model.fit(X_arr, y_arr)

    train_r2 = model.score(X_arr, y_arr)
    cv_mean_r2 = cv_scores.mean()
    overfit_ratio = train_r2 / cv_mean_r2 if cv_mean_r2 > 1e-6 else float("inf")

    # 变量选择结果
    selected = [i for i, c in enumerate(model.coef_) if abs(c) > 1e-8]
    dropped = [i for i, c in enumerate(model.coef_) if abs(c) < 1e-8]
    n_selected = len(selected)

    if n_selected == 0:
        warnings.warn(
            "[Lasso 警告] 所有系数均被压缩为 0。请尝试减小 alpha 值，或改用 ridge_regression()。",
            UserWarning,
        )

    if overfit_ratio > 1.5:
        warnings.warn(
            f"[过拟合警告] 训练 R^2={train_r2:.4f}, 交叉验证 R^2={cv_mean_r2:.4f}, "
            f"比值={overfit_ratio:.2f} > 1.5。建议增大 alpha 或减少特征。",
            UserWarning,
        )

    print(f"[Lasso] alpha={alpha:.4f}, 训练 R^2={train_r2:.4f}, "
          f"{cv}折 CV 平均 R^2={cv_mean_r2:.4f} (std={cv_scores.std():.4f}), "
          f"保留 {n_selected}/{p} 个特征")

    return {
        "coef": np.concatenate([[model.intercept_], model.coef_]),
        "intercept": model.intercept_,
        "alpha": alpha,
        "selected_features": selected,
        "dropped_features": dropped,
        "cv_scores": cv_scores,
        "train_r2": train_r2,
        "cv_mean_r2": cv_mean_r2,
        "overfit_ratio": overfit_ratio,
        "model": model,
    }


# ============================================================================
# 4. 主成分分析 (PCA)
# ============================================================================

def pca_analysis(
    X: Union[np.ndarray, pd.DataFrame],
    n_components: Optional[int] = None,
) -> dict:
    """
    主成分分析（PCA）降维与可视化。

    自动标准化数据，输出主成分得分、方差解释率、载荷矩阵，
    并绘制碎石图保存至 figures/pca_scree.png。

    Parameters
    ----------
    X : np.ndarray (n, p) or pd.DataFrame
        原始数据矩阵。
    n_components : int, optional
        保留的主成分数。默认 None 即保留所有成分。

    Returns
    -------
    result : dict
        keys:
        - scores : 主成分得分矩阵
        - explained_variance_ratio : 各主成分方差解释率
        - cumulative_variance : 累积方差解释率
        - loadings : 载荷矩阵（变量在主成分上的权重）
        - components : 主成分方向向量
        - n_components : 实际保留的主成分数
        - model : 训练好的 PCA 对象

    Notes
    -----
    - 适用场景：高维数据降维、变量间共线性消除、数据可视化。
    - 建议根据累积方差 > 85% 或碎石图"肘部"选取 n_components。

    Examples
    --------
    >>> from sklearn.datasets import load_iris
    >>> X = load_iris().data
    >>> res = pca_analysis(X, n_components=2)
    >>> print(res['explained_variance_ratio'])
    """
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    if isinstance(X, pd.DataFrame):
        feature_names = X.columns.tolist()
        X_arr = X.values.astype(float)
    else:
        X_arr = np.asarray(X, dtype=float)
        feature_names = [f"X{i+1}" for i in range(X_arr.shape[1])]

    # 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_arr)

    # PCA
    max_comp = min(X_arr.shape[0], X_arr.shape[1])
    if n_components is None:
        n_components = max_comp
    n_components = min(n_components, max_comp)

    pca = PCA(n_components=n_components)
    scores = pca.fit_transform(X_scaled)

    # 累计方差解释率
    cumulative = np.cumsum(pca.explained_variance_ratio_)

    # 载荷矩阵
    loadings = pd.DataFrame(
        pca.components_.T,
        index=feature_names,
        columns=[f"PC{i+1}" for i in range(pca.n_components_)],
    )

    # 碎石图
    _set_chinese_font()
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # 碎石图 + 累积方差
    ax1 = axes[0]
    x_ticks = np.arange(1, len(pca.explained_variance_ratio_) + 1)
    bars = ax1.bar(x_ticks, pca.explained_variance_ratio_, color="steelblue",
                   alpha=0.8, label="个体解释率")
    ax1.plot(x_ticks, cumulative, "ro-", markersize=5, label="累积解释率")
    ax1.axhline(y=0.85, color="gray", linestyle="--", alpha=0.6, label="85% 阈值")
    ax1.set_xlabel("主成分序号")
    ax1.set_ylabel("方差解释率")
    ax1.set_title("PCA 碎石图")
    ax1.legend(fontsize=8)
    ax1.grid(axis="y", alpha=0.3)
    for bar, val in zip(bars, pca.explained_variance_ratio_):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f"{val:.1%}", ha="center", fontsize=8)

    # 载荷热力图
    ax2 = axes[1]
    im = ax2.imshow(loadings.values, cmap="RdBu_r", aspect="auto", vmin=-1, vmax=1)
    ax2.set_xticks(range(loadings.shape[1]))
    ax2.set_xticklabels(loadings.columns)
    ax2.set_yticks(range(loadings.shape[0]))
    ax2.set_yticklabels(loadings.index)
    ax2.set_title("载荷矩阵热力图")
    plt.colorbar(im, ax=ax2, shrink=0.8, label="载荷值")

    for i in range(loadings.shape[0]):
        for j in range(loadings.shape[1]):
            ax2.text(j, i, f"{loadings.values[i, j]:.2f}",
                     ha="center", va="center", fontsize=8,
                     color="white" if abs(loadings.values[i, j]) > 0.5 else "black")

    plt.tight_layout()
    import os
    os.makedirs("../figures", exist_ok=True)
    plt.savefig("../figures/pca_scree.png", dpi=150, bbox_inches="tight")
    plt.close()

    return {
        "scores": scores,
        "explained_variance_ratio": pca.explained_variance_ratio_,
        "cumulative_variance": cumulative,
        "loadings": loadings,
        "components": pca.components_,
        "n_components": pca.n_components_,
        "model": pca,
    }


# ============================================================================
# 5. K-means 聚类
# ============================================================================

def kmeans_cluster(
    X: Union[np.ndarray, pd.DataFrame],
    n_clusters: int = 3,
    random_state: int = 0,
) -> dict:
    """
    K-means 聚类分析。

    自动标准化后进行聚类，输出标签、中心及轮廓系数。

    Parameters
    ----------
    X : np.ndarray (n, p) or pd.DataFrame
        数据矩阵。
    n_clusters : int
        聚类数，默认 3。
    random_state : int
        随机种子。

    Returns
    -------
    result : dict
        keys:
        - labels : 各样本的簇标签
        - centers : 簇中心（原始尺度）
        - silhouette : 轮廓系数 [-1, 1]，越接近 1 聚类质量越好
        - inertia : 簇内平方和
        - model : 训练好的 KMeans 对象

    Notes
    -----
    - 适用场景：客户分群、图像分割、样本分类等无监督分类任务。
    - 建议配合肘部法则或轮廓系数选最佳 k 值。

    Examples
    --------
    >>> from sklearn.datasets import load_iris
    >>> X = load_iris().data
    >>> res = kmeans_cluster(X, n_clusters=3)
    >>> print(f"轮廓系数: {res['silhouette']:.4f}")
    """
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    if isinstance(X, pd.DataFrame):
        X_arr = X.values.astype(float)
    else:
        X_arr = np.asarray(X, dtype=float)

    # 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_arr)

    # K-means
    km = KMeans(n_clusters=n_clusters, random_state=random_state, n_init="auto")
    labels = km.fit_predict(X_scaled)

    # 簇中心还原到原始尺度
    centers = scaler.inverse_transform(km.cluster_centers_)

    # 轮廓系数
    silhouette = silhouette_score(X_scaled, labels) if n_clusters > 1 else 0.0

    # 可视化（使用前两个主成分）
    _set_chinese_font()
    import matplotlib.pyplot as plt

    from sklearn.decomposition import PCA
    pca_viz = PCA(n_components=2)
    X_pca = pca_viz.fit_transform(X_scaled)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    # 聚类散点图
    ax1 = axes[0]
    colors = plt.cm.tab10(np.linspace(0, 1, n_clusters))
    for k in range(n_clusters):
        mask = labels == k
        ax1.scatter(X_pca[mask, 0], X_pca[mask, 1], c=[colors[k]],
                    label=f"簇 {k+1}", alpha=0.7, edgecolors="k", linewidths=0.3)
    ax1.set_xlabel("PC1")
    ax1.set_ylabel("PC2")
    ax1.set_title(f"K-means 聚类结果 (k={n_clusters})")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    # 轮廓系数条状图
    ax2 = axes[1]
    from sklearn.metrics import silhouette_samples
    sample_silhouette = silhouette_samples(X_scaled, labels)
    y_lower = 10
    for k in range(n_clusters):
        k_values = sample_silhouette[labels == k]
        k_values.sort()
        size_k = len(k_values)
        y_upper = y_lower + size_k
        ax2.fill_betweenx(np.arange(y_lower, y_upper), 0, k_values,
                          facecolor=colors[k], alpha=0.7, label=f"簇 {k+1}")
        y_lower = y_upper + 10
    ax2.axvline(x=silhouette, color="red", linestyle="--", linewidth=1.2,
                label=f"平均轮廓系数 = {silhouette:.3f}")
    ax2.set_xlabel("轮廓系数")
    ax2.set_ylabel("样本")
    ax2.set_title("各簇轮廓系数分布")
    ax2.legend(fontsize=8)

    plt.tight_layout()
    import os
    os.makedirs("../figures", exist_ok=True)
    plt.savefig("../figures/kmeans_cluster.png", dpi=150, bbox_inches="tight")
    plt.close()

    return {
        "labels": labels,
        "centers": centers,
        "silhouette": silhouette,
        "inertia": km.inertia_,
        "model": km,
    }


# ============================================================================
# 6. 层次聚类
# ============================================================================

def hierarchical_cluster(
    X: Union[np.ndarray, pd.DataFrame],
    method: str = "ward",
    n_clusters: Optional[int] = None,
) -> dict:
    """
    层次聚类分析（含树状图）。

    使用 scipy 计算距离矩阵并执行层次聚类，绘制树状图。

    Parameters
    ----------
    X : np.ndarray (n, p) or pd.DataFrame
        数据矩阵。
    method : str
        簇间距离度量方法：
        - "ward" : Ward 最小方差法（默认）
        - "complete" : 最大距离法
        - "average" : 平均距离法
        - "single" : 最小距离法
    n_clusters : int, optional
        若指定，则对该层切分并返回聚类标签。

    Returns
    -------
    result : dict
        keys:
        - linkage_matrix : 连接矩阵 (n-1, 4)
        - labels : 若指定 n_clusters 则返回标签，否则 None
        - dendrogram : 树状图对象

    Notes
    -----
    - 适用场景：样本数较少的聚类问题（n < 500），需要可视化聚类层次结构时。
    - 树状图保存至 figures/hierarchical_dendrogram.png。

    Examples
    --------
    >>> from sklearn.datasets import load_iris
    >>> X = load_iris().data[:30]  # 取子集便于展示
    >>> res = hierarchical_cluster(X, method="ward", n_clusters=3)
    """
    from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
    from scipy.spatial.distance import pdist
    from sklearn.preprocessing import StandardScaler

    if isinstance(X, pd.DataFrame):
        X_arr = X.values.astype(float)
    else:
        X_arr = np.asarray(X, dtype=float)

    if X_arr.shape[0] < 2:
        raise ValueError("至少需要 2 个样本进行层次聚类。")

    # 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_arr)

    # 层次聚类
    Z = linkage(X_scaled, method=method)

    # 切分标签
    labels = None
    if n_clusters is not None:
        labels = fcluster(Z, t=n_clusters, criterion="maxclust") - 1  # 0-based

    # 树状图
    _set_chinese_font()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(14, 6))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dn = dendrogram(Z, ax=ax, leaf_rotation=90, leaf_font_size=8,
                        color_threshold=None if n_clusters is None else
                        0.5 * (Z[-n_clusters + 1, 2] + Z[-n_clusters, 2]) if n_clusters > 1 else 0)

    ax.set_title(f"层次聚类树状图 (method = '{method}')")
    ax.set_xlabel("样本索引")
    ax.set_ylabel("距离")
    ax.grid(axis="y", alpha=0.2)

    plt.tight_layout()
    import os
    os.makedirs("../figures", exist_ok=True)
    plt.savefig("../figures/hierarchical_dendrogram.png", dpi=150, bbox_inches="tight")
    plt.close()

    return {
        "linkage_matrix": Z,
        "labels": labels,
        "dendrogram": dn,
    }


# ============================================================================
# 7. 相关性热力图
# ============================================================================

def correlation_heatmap(
    df: pd.DataFrame,
    method: str = "pearson",
    annot: bool = True,
    figsize: Tuple[int, int] = (10, 8),
    cmap: str = "RdBu_r",
    save_path: Optional[str] = None,
) -> np.ndarray:
    """
    相关性矩阵热力图。

    计算变量间的相关系数矩阵并以热力图形式呈现。

    Parameters
    ----------
    df : pd.DataFrame
        输入数据框（仅数值列参与计算）。
    method : str
        相关系数类型："pearson"（默认）、"spearman"、"kendall"。
    annot : bool
        是否在格内显示数值，默认 True。
    figsize : tuple
        图像尺寸。
    cmap : str
        颜色映射。
    save_path : str, optional
        保存路径，默认保存至 figures/correlation_heatmap.png。

    Returns
    -------
    corr_matrix : np.ndarray
        相关系数矩阵。

    Notes
    -----
    - 适用场景：探索性数据分析（EDA），识别变量间的线性/单调关系。
    - 自动检测非数值列并排除，给出提示。

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"A": [1,2,3], "B": [4,5,6], "C": [7,8,9]})
    >>> corr = correlation_heatmap(df)
    """
    # 排除非数值列
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    non_numeric = [c for c in df.columns if c not in numeric_cols]
    if non_numeric:
        print(f"[相关性热力图] 已排除非数值列: {non_numeric}")

    if len(numeric_cols) < 2:
        raise ValueError(f"至少需要 2 个数值列，当前仅有 {len(numeric_cols)}。")

    corr_matrix = df[numeric_cols].corr(method=method)

    _set_chinese_font()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(corr_matrix.values, cmap=cmap, aspect="auto", vmin=-1, vmax=1)

    # 标注
    if annot:
        for i in range(len(numeric_cols)):
            for j in range(len(numeric_cols)):
                val = corr_matrix.values[i, j]
                text_color = "white" if abs(val) > 0.6 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=9, color=text_color)

    ax.set_xticks(range(len(numeric_cols)))
    ax.set_xticklabels(numeric_cols, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(numeric_cols)))
    ax.set_yticklabels(numeric_cols, fontsize=9)
    ax.set_title(f"变量相关性热力图 ({method.capitalize()})", fontsize=13)

    plt.colorbar(im, ax=ax, shrink=0.8, label="相关系数")

    plt.tight_layout()
    import os
    if save_path is None:
        os.makedirs("../figures", exist_ok=True)
        save_path = "../figures/correlation_heatmap.png"
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[相关性热力图] 已保存至 {save_path}")

    return corr_matrix.values


# ============================================================================
# 8. 过拟合检查（通用）
# ============================================================================

def check_overfit(
    train_metrics: dict,
    test_metrics: dict,
    threshold: float = 2.0,
    metric_keys: tuple = ("RMSE", "MAE", "R2"),
) -> dict:
    """
    通用过拟合诊断：对比训练集和测试集（或交叉验证）的误差指标。

    若测试误差是训练误差的 threshold 倍以上，发出过拟合警告。

    Parameters
    ----------
    train_metrics : dict
        训练集指标，由 evaluate_model() 返回或自定义。须包含 metric_keys 中的键。
    test_metrics : dict
        测试集（或交叉验证）指标，须包含相同键。
    threshold : float
        过拟合阈值。当 test_error / train_error > threshold 时触发警告。
        默认 2.0（测试误差超过训练误差 2 倍）。
    metric_keys : tuple
        用于比较的指标键名，默认 ("RMSE", "MAE", "R2")。
        R2 的比较方向相反（test_R2 低于 train_R2 越多越可疑）。

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
    - 对于 R2，ratio = train / test（因为 R2 越高越好，降低即过拟合迹象）。
    - 如果差异过大（test/train > 2x），会主动打印警告信息。

    Examples
    --------
    >>> from prediction import evaluate_model
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
            # R2 越高越好：test 显著低于 train 即过拟合
            if train_val > 1e-6:
                ratio = train_val / max(test_val, 1e-6)
            else:
                ratio = 1.0
        else:
            # 误差类指标：越低越好，test 高于 train 即过拟合
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
        print("[过拟合检查] 通过：训练集与测试集误差指标在合理范围内，未检测到明显过拟合。")

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

    _set_chinese_font()
    warnings.filterwarnings("ignore")
    np.set_printoptions(precision=4, suppress=True)

    print("=" * 60)
    print("统计分析模块 — 测试示例")
    print("=" * 60)

    # ---- 加载 iris 数据 ----
    from sklearn.datasets import load_iris

    iris = load_iris()
    X_iris = iris.data
    y_iris = iris.target
    feature_names = iris.feature_names
    df_iris = pd.DataFrame(X_iris, columns=feature_names)
    df_iris["species"] = y_iris

    print(f"\n数据集: Iris (n={X_iris.shape[0]}, p={X_iris.shape[1]})")
    print(f"特征: {feature_names}")

    # ======== 1. 多元回归 ========
    print("\n" + "-" * 40)
    print("[1] 多元线性回归")
    print("-" * 40)
    # 用前三个特征预测第四个
    X_reg = df_iris[feature_names[:3]]
    y_reg = df_iris[feature_names[3]]

    try:
        res_reg = multiple_regression(X_reg, y_reg, standardize=True)
        print(f"  R^2 = {res_reg['r_squared']:.4f}")
        print(f"  调整 R^2 = {res_reg['adj_r_squared']:.4f}")
        print(f"  F 统计量 = {res_reg['f_stat']:.2f}  (p = {res_reg['f_pvalue']:.2e})")
        print(f"\n  系数与显著性:")
        for i, name in enumerate(["截距"] + [f"{n}" for n in feature_names[:3]]):
            p_val = res_reg["p_values"].values[i]
            sig = "***" if p_val < 0.001 else ("**" if p_val < 0.01 else ("*" if p_val < 0.05 else ""))
            print(f"    {name:<18} coeff = {res_reg['coef'].values[i]:>8.4f}  p = {p_val:.4f} {sig}")
        print(f"\n  VIF 诊断:")
        print(res_reg["vif"].to_string(index=False))
    except ImportError:
        print("  [跳过] 未安装 statsmodels")

    # ======== 2. PCA ========
    print("\n" + "-" * 40)
    print("[2] 主成分分析 (PCA)")
    print("-" * 40)
    res_pca = pca_analysis(X_iris, n_components=4)
    print(f"  方差解释率: {np.round(res_pca['explained_variance_ratio'] * 100, 2)}%")
    print(f"  累积解释率: {np.round(res_pca['cumulative_variance'] * 100, 2)}%")
    print(f"  前 2 个主成分即解释 {res_pca['cumulative_variance'][1]*100:.1f}% 的方差")
    print(f"\n  载荷矩阵:")
    print(res_pca["loadings"].to_string())

    # ======== 3. K-means 聚类 ========
    print("\n" + "-" * 40)
    print("[3] K-means 聚类")
    print("-" * 40)
    res_km = kmeans_cluster(X_iris, n_clusters=3, random_state=42)
    print(f"  轮廓系数: {res_km['silhouette']:.4f}")
    print(f"  簇内平方和: {res_km['inertia']:.2f}")
    print(f"  簇大小: {np.bincount(res_km['labels'])}")
    # 与真实标签对比
    from sklearn.metrics import adjusted_rand_score
    ari = adjusted_rand_score(y_iris, res_km["labels"])
    print(f"  调整兰德指数 (ARI): {ari:.4f}  (与真实分类对比)")

    # ======== 4. 层次聚类 ========
    print("\n" + "-" * 40)
    print("[4] 层次聚类")
    print("-" * 40)
    # 取子集便于展示树状图
    indices = np.random.default_rng(0).choice(len(X_iris), size=40, replace=False)
    X_sub = X_iris[indices]
    res_hc = hierarchical_cluster(X_sub, method="ward", n_clusters=3)
    if res_hc["labels"] is not None:
        print(f"  聚类标签分布: {np.bincount(res_hc['labels'])}")

    # ======== 5. 相关性热力图 ========
    print("\n" + "-" * 40)
    print("[5] 相关性热力图")
    print("-" * 40)
    corr = correlation_heatmap(df_iris[feature_names], annot=True)
    print(f"  相关系数矩阵:\n{np.round(corr, 3)}")

    # ======== 汇总 ========
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"  多元回归 R^2          : {res_reg['r_squared']:.4f}" if 'res_reg' in dir() else "  [跳过]")
    print(f"  PCA 前2成分累积方差    : {res_pca['cumulative_variance'][1]*100:.2f}%")
    print(f"  K-means 轮廓系数      : {res_km['silhouette']:.4f}")
    print(f"  K-means ARI (vs 真实) : {ari:.4f}")

    print(f"\n图表已保存至 figures/ 目录:")
    print(f"  - pca_scree.png")
    print(f"  - kmeans_cluster.png")
    print(f"  - hierarchical_dendrogram.png")
    print(f"  - correlation_heatmap.png")
    print("=" * 60)
