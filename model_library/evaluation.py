"""
综合评价模型库 — evaluation.py
================================
包含熵权法、TOPSIS、熵权-TOPSIS、模糊综合评价、层次分析法(AHP)。
用于数学建模竞赛中的多指标综合评价与决策问题。
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional, Union, Callable


# ============================================================================
# 1. 熵权法
# ============================================================================

def entropy_weight(matrix: np.ndarray) -> np.ndarray:
    """
    熵权法计算客观权重。

    基于信息熵原理：指标变异程度越大，信息熵越小，所含信息量越大，权重越高。

    Parameters
    ----------
    matrix : np.ndarray, shape (n_samples, n_indicators)
        原始数据矩阵，每行为一个样本，每列为一个指标。

    Returns
    -------
    weights : np.ndarray, shape (n_indicators,)
        各指标的客观权重，总和为 1。

    Notes
    -----
    - 内部自动进行 min-max 归一化。
    - 若某指标在所有样本上取值相同（熵 = 1），权重会被设为 0。
    - 适用于数据波动越大越重要的场景，无法反映决策者主观偏好。

    Examples
    --------
    >>> data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    >>> entropy_weight(data)
    array([0.333..., 0.333..., 0.333...])
    """
    matrix = np.asarray(matrix, dtype=float)
    n, m = matrix.shape

    # Min-max 归一化（正向化），避免负值和零值
    v_min = matrix.min(axis=0)
    v_max = matrix.max(axis=0)
    denom = v_max - v_min
    # 若 denom 为 0，则该指标所有值相同，直接返回全零列
    denom[denom == 0] = 1.0
    p = (matrix - v_min) / denom

    # 平移防零（避免 log(0)）
    p += 1e-10
    p_sum = p.sum(axis=0)
    p = p / p_sum

    # 计算熵值
    k = 1.0 / np.log(n)
    e = -k * np.sum(p * np.log(p), axis=0)
    e = np.clip(e, 0, 1)

    # 差异系数 → 权重
    d = 1 - e
    if np.all(d == 0):
        # 所有指标完全相同 → 等权
        return np.ones(m) / m

    weights = d / d.sum()
    return weights


# ============================================================================
# 2. TOPSIS 综合评价
# ============================================================================

def topsis(matrix: np.ndarray,
           weights: Optional[np.ndarray] = None,
           impacts: Optional[np.ndarray] = None) -> np.ndarray:
    """
    TOPSIS 综合评价（逼近理想解排序法）。

    通过计算各方案到正理想解和负理想解的加权欧氏距离，得到相对贴近度。

    Parameters
    ----------
    matrix : np.ndarray, shape (n_samples, n_indicators)
        原始数据矩阵（建议先自行正向化处理），每行为一个方案。
    weights : np.ndarray, shape (n_indicators,), optional
        指标权重向量，默认等权。
    impacts : np.ndarray, shape (n_indicators,), optional
        指标方向：1 表示正向指标（越大越好），-1 表示负向指标（越小越好）。
        默认全为 1。

    Returns
    -------
    scores : np.ndarray, shape (n_samples,)
        各方案的相对贴近度得分，值越大方案越优。

    Notes
    -----
    - 内部会先做向量归一化（除以列 L2 范数）。
    - 数值稳定：对 L2 范数为 0 的列不做归一化。

    Examples
    --------
    >>> matrix = np.array([[2, 100], [3, 80], [1, 120]])
    >>> weights = np.array([0.6, 0.4])
    >>> impacts = np.array([1, -1])
    >>> topsis(matrix, weights, impacts)
    array([0.52..., 0.70..., 0.21...])
    """
    matrix = np.asarray(matrix, dtype=float)
    n, m = matrix.shape

    if weights is None:
        weights = np.ones(m) / m
    else:
        weights = np.asarray(weights, dtype=float)
        weights = weights / weights.sum()

    if impacts is None:
        impacts = np.ones(m, dtype=int)

    impacts = np.asarray(impacts, dtype=int)

    # 向量归一化（L2 范数）
    col_norm = np.sqrt(np.sum(matrix ** 2, axis=0))
    col_norm[col_norm == 0] = 1.0
    normed = matrix / col_norm

    # 加权归一化矩阵
    weighted = normed * weights

    # 正理想解与负理想解
    ideal_best = np.where(impacts == 1, weighted.max(axis=0), weighted.min(axis=0))
    ideal_worst = np.where(impacts == 1, weighted.min(axis=0), weighted.max(axis=0))

    # 到正、负理想解的欧氏距离
    dist_best = np.sqrt(np.sum((weighted - ideal_best) ** 2, axis=1))
    dist_worst = np.sqrt(np.sum((weighted - ideal_worst) ** 2, axis=1))

    # 相对贴近度
    denom = dist_best + dist_worst
    denom[denom == 0] = 1e-10
    scores = dist_worst / denom

    return scores


# ============================================================================
# 3. 熵权-TOPSIS 组合模型
# ============================================================================

def entropy_topsis(
    data: Union[np.ndarray, pd.DataFrame],
    impacts: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    熵权-TOPSIS 组合综合评价模型。

    先用熵权法从数据中提取客观权重，再用 TOPSIS 计算相对贴近度得分。
    一步完成从原始数据到最终排名的全流程。

    Parameters
    ----------
    data : np.ndarray (n, m) or pd.DataFrame
        原始数据矩阵或 DataFrame。若为 DataFrame，自动提取 values。
    impacts : np.ndarray, shape (m,), optional
        指标方向：1 正向，-1 负向。默认全为正向。

    Returns
    -------
    scores : np.ndarray, shape (n,)
        各方案的 TOPSIS 相对贴近度得分。
    weights : np.ndarray, shape (m,)
        熵权法计算出的客观权重。

    Notes
    -----
    - 适用于完全基于数据驱动的评价场景，无需主观赋权。
    - 若某个指标全为同一值，权重为 0。

    Examples
    --------
    >>> data = np.array([[0.8, 90, 5], [0.6, 80, 3], [0.9, 95, 7]])
    >>> impacts = np.array([1, 1, -1])
    >>> scores, w = entropy_topsis(data, impacts)
    >>> scores
    array([0.57..., 0.04..., 0.87...])
    """
    if isinstance(data, pd.DataFrame):
        matrix = data.values.astype(float)
    else:
        matrix = np.asarray(data, dtype=float)

    if impacts is None:
        impacts = np.ones(matrix.shape[1], dtype=int)

    weights = entropy_weight(matrix)
    scores = topsis(matrix, weights, impacts)
    return scores, weights


# ============================================================================
# 4. 模糊综合评价
# ============================================================================

def fuzzy_evaluation(
    matrix: np.ndarray,
    membership_funcs: List[Callable[[np.ndarray], np.ndarray]],
    weights: np.ndarray
) -> np.ndarray:
    """
    模糊综合评价。

    利用隶属度函数将各指标的精确值转化为对各评价等级的隶属度，
    再通过模糊合成得到最终评价等级。

    Parameters
    ----------
    matrix : np.ndarray, shape (n_samples, n_indicators)
        样本数据矩阵。
    membership_funcs : list of callable
        对各评价等级的隶属度函数列表。
        长度 = n_levels，每个函数签名为 f(x: np.ndarray) -> np.ndarray
        返回 shape (n_indicators,) 的隶属度。
    weights : np.ndarray, shape (n_indicators,)
        各指标权重。

    Returns
    -------
    levels : np.ndarray, shape (n_samples,)
        各样本的评价等级（0 到 n_levels - 1），取最大隶属度原则。

    Notes
    -----
    - 权重先归一化。
    - 合成算子使用加权平均型 M(·, +)。
    - 去模糊化采用最大隶属度原则，平局时取较高等级。

    Examples
    --------
    >>> data = np.array([[7, 8], [3, 4]])
    >>> # 两个等级：低和高（以均值为阈值线性分段）
    >>> def low(x): return np.maximum(1 - x / 10, 0)
    >>> def high(x): return np.minimum(x / 10, 1)
    >>> fuzzy_evaluation(data, [low, high], np.array([0.5, 0.5]))
    array([1, 0])
    """
    matrix = np.asarray(matrix, dtype=float)
    weights = np.asarray(weights, dtype=float)
    weights = weights / weights.sum()

    n_samples, m = matrix.shape
    n_levels = len(membership_funcs)

    # 对每个样本、每个等级计算综合隶属度
    combined = np.zeros((n_samples, n_levels))

    for k, func in enumerate(membership_funcs):
        for i in range(n_samples):
            mu = func(matrix[i])
            combined[i, k] = np.sum(weights * mu)

    # 去模糊化：最大隶属度原则
    levels = np.argmax(combined, axis=1)
    return levels


# ============================================================================
# 5. 层次分析法（AHP）
# ============================================================================

def ahp(matrix: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    层次分析法（AHP）计算权重及一致性检验。

    基于 Saaty 1-9 标度，通过判断矩阵的特征向量得到各因素的相对权重。

    Parameters
    ----------
    matrix : np.ndarray, shape (n, n)
        成对比较判断矩阵（正互反矩阵）。
        元素 a_ij 表示因素 i 相对于因素 j 的重要程度。
        Saaty 标度：1 同等重要，3 稍重要，5 明显重要，7 强烈重要，9 极端重要。

    Returns
    -------
    weights : np.ndarray, shape (n,)
        归一化权重向量（和 = 1）。
    cr : float
        一致性比率 CR = CI / RI。
        若 CR < 0.1，一致性可接受；否则判断矩阵需要修正。

    Notes
    -----
    - 使用特征向量法（最大特征值对应的特征向量）。
    - RI 值针对 1~15 阶矩阵内建。

    References
    ----------
    Saaty, T. L. (1980). The Analytic Hierarchy Process.

    Examples
    --------
    >>> matrix = np.array([[1, 3, 5],
    ...                    [1/3, 1, 3],
    ...                    [1/5, 1/3, 1]])
    >>> w, cr = ahp(matrix)
    >>> w
    array([0.63..., 0.25..., 0.10...])
    >>> cr < 0.1
    True
    """
    A = np.asarray(matrix, dtype=float)
    n = A.shape[0]

    # 随机一致性指标 RI（1~15 阶）
    RI_TABLE = {
        1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12,
        6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49,
        11: 1.51, 12: 1.48, 13: 1.56, 14: 1.57, 15: 1.59,
    }
    ri = RI_TABLE.get(n, 1.59)

    # 特征值和特征向量
    eigenvals, eigenvecs = np.linalg.eig(A)
    lambda_max = np.max(eigenvals.real)
    idx = np.argmax(eigenvals.real)
    principal_vec = eigenvecs[:, idx].real

    # 归一化为权重
    weights = np.abs(principal_vec) / np.abs(principal_vec).sum()

    # 一致性检验
    ci = (lambda_max - n) / (n - 1) if n > 2 else 0.0
    cr = ci / ri if ri != 0 else 0.0

    return weights, cr


# ============================================================================
# 测试示例
# ============================================================================

if __name__ == "__main__":
    np.set_printoptions(precision=4, suppress=True)

    print("=" * 60)
    print("综合评价模型库 — 测试示例")
    print("=" * 60)

    # ----- 模拟数据 -----
    # 5 个方案，4 个评价指标
    # 指标1: 成本（负向）  指标2: 效率（正向）
    # 指标3: 可靠性（正向） 指标4: 故障率（负向）
    rng = np.random.default_rng(42)
    data = np.column_stack([
        rng.uniform(50, 150, 5),   # 成本
        rng.uniform(70, 100, 5),   # 效率
        rng.uniform(0.85, 0.99, 5), # 可靠性
        rng.uniform(0.01, 0.15, 5), # 故障率
    ])
    impacts = np.array([-1, 1, 1, -1])  # 负向、正向、正向、负向
    indicator_names = ["成本", "效率", "可靠性", "故障率"]

    print(f"\n原始数据 (5 方案 × 4 指标):\n{data}\n")
    print(f"指标方向: {impacts}  (1=正向, -1=负向)\n")

    # ---- 1. 熵权法 ----
    w_entropy = entropy_weight(data)
    print(f"[熵权法] 各指标权重: {w_entropy}\n")

    # ---- 2. TOPSIS ----
    scores_topsis = topsis(data, weights=w_entropy, impacts=impacts)
    rank_topsis = np.argsort(-scores_topsis) + 1
    print(f"[TOPSIS] 相对贴近度: {scores_topsis}")
    print(f"[TOPSIS] 排名 (1 最优): {rank_topsis}\n")

    # ---- 3. 熵权-TOPSIS 组合 ----
    scores_combo, w_combo = entropy_topsis(data, impacts=impacts)
    rank_combo = np.argsort(-scores_combo) + 1
    print(f"[熵权-TOPSIS] 权重: {w_combo}")
    print(f"[熵权-TOPSIS] 得分: {scores_combo}")
    print(f"[熵权-TOPSIS] 排名 (1 最优): {rank_combo}\n")

    # ---- 4. 模糊综合评价 ----
    # 定义三个等级：差(0)、中(1)、好(2)
    # 使用半梯形隶属度函数
    def poor(x):
        return np.maximum((60 - x) / 40, 0)

    def medium(x):
        return np.maximum(1 - np.abs(x - 75) / 25, 0)

    def good(x):
        return np.maximum((x - 80) / 40, 0)

    levels = fuzzy_evaluation(data, [poor, medium, good], w_entropy)
    level_map = {0: "差", 1: "中", 2: "好"}
    print(f"[模糊综合评价] 各方案评价等级: {[level_map[l] for l in levels]}\n")

    # ---- 5. AHP 层次分析法 ----
    # 4 × 4 判断矩阵 (Saaty 1-9 标度)
    # 效率最重要，其次可靠性，成本和故障率同等
    ahp_matrix = np.array([
        [1,   1/3, 1/2, 1  ],
        [3,   1,   2,   3  ],
        [2,   1/2, 1,   2  ],
        [1,   1/3, 1/2, 1  ],
    ])
    w_ahp, cr = ahp(ahp_matrix)
    passed = "通过" if cr < 0.1 else "未通过"
    print(f"[AHP] 判断矩阵:\n{ahp_matrix}")
    print(f"[AHP] 权重: {w_ahp}")
    print(f"[AHP] λ_max = {np.max(np.linalg.eigvals(ahp_matrix)).real:.4f}")
    print(f"[AHP] CR = {cr:.4f} ({passed})\n")

    # ---- 汇总对比 ----
    print("=" * 60)
    print("权重对比汇总")
    print("-" * 60)
    df_weights = pd.DataFrame({
        "指标": indicator_names,
        "熵权法": w_entropy,
        "AHP": w_ahp,
    })
    df_weights["差异"] = np.abs(df_weights["熵权法"] - df_weights["AHP"])
    print(df_weights.to_string(index=False))
    print("=" * 60)

    # ---- 熵权-TOPSIS 结果排序 ----
    print("\n熵权-TOPSIS 最终排序:")
    for rank, score in enumerate(np.sort(scores_combo)[::-1], 1):
        idx = np.where(scores_combo == score)[0][0]
        print(f"  第 {rank} 名: 方案 {idx + 1} (得分: {score:.4f})")
    print("=" * 60)
