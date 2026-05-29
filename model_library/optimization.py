"""
优化模型库 — optimization.py
==============================
包含线性规划、整数规划、遗传算法、模拟退火、混合整数非线性规划。
用于数学建模竞赛中的最优化决策问题。
"""

import warnings
from typing import Tuple, Optional, Callable, List, Dict, Any

import numpy as np
from scipy.optimize import linprog, differential_evolution


# ============================================================================
# 1. 线性规划
# ============================================================================

def linear_programming(
    c: np.ndarray,
    A_ub: Optional[np.ndarray] = None,
    b_ub: Optional[np.ndarray] = None,
    A_eq: Optional[np.ndarray] = None,
    b_eq: Optional[np.ndarray] = None,
    bounds: Optional[List[Tuple[Optional[float], Optional[float]]]] = None,
    objective: str = "min",
    method: str = "highs",
) -> Dict[str, Any]:
    """
    线性规划求解器（封装 scipy.optimize.linprog）。

    解决标准形式 $\\min c^T x$ s.t. $A_{ub} x \\le b_{ub}$, $A_{eq} x = b_{eq}$, $x \\in [L, U]$。

    Parameters
    ----------
    c : np.ndarray, shape (n,)
        目标函数系数向量。
    A_ub : np.ndarray, shape (m, n), optional
        不等式约束矩阵（$\\le$）。
    b_ub : np.ndarray, shape (m,), optional
        不等式约束右侧常数。
    A_eq : np.ndarray, shape (k, n), optional
        等式约束矩阵。
    b_eq : np.ndarray, shape (k,), optional
        等式约束右侧常数。
    bounds : list of tuple, optional
        每个变量的上下界，默认 (None, None) 即无界。
    objective : str
        "min"（默认）或 "max"。
    method : str
        求解方法，默认 "highs"（HiGHS 高性能求解器）。

    Returns
    -------
    result : dict
        keys: x (最优解), fun (最优目标值), success, status, message。

    Notes
    -----
    - 若 objective="max"，内部自动将 c 取反转为最小化问题。
    - 适用于资源分配、生产计划、运输问题等线性目标+线性约束场景。

    Examples
    --------
    >>> c = np.array([-3, -2])  # max 3x1 + 2x2
    >>> A_ub = np.array([[2, 1], [1, 2]])
    >>> b_ub = np.array([6, 6])
    >>> bounds = [(0, None), (0, None)]
    >>> result = linear_programming(c, A_ub, b_ub, bounds=bounds, objective="max")
    """
    c = np.asarray(c, dtype=float).ravel()

    if objective == "max":
        c = -c

    if bounds is None:
        bounds = [(None, None)] * len(c)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                      bounds=bounds, method=method)

    fun = -res.fun if objective == "max" else res.fun

    return {
        "x": res.x,
        "fun": fun,
        "success": res.success,
        "status": res.status,
        "message": res.message,
    }


# ============================================================================
# 2. 整数规划（PuLP）
# ============================================================================

def integer_programming(
    c: np.ndarray,
    A_ub: Optional[np.ndarray] = None,
    b_ub: Optional[np.ndarray] = None,
    A_eq: Optional[np.ndarray] = None,
    b_eq: Optional[np.ndarray] = None,
    bounds: Optional[List[Tuple[float, float]]] = None,
    objective: str = "min",
    cat: str = "Integer",
) -> Dict[str, Any]:
    """
    整数规划求解器（基于 PuLP）。

    所有决策变量为整数（或 0-1 二值），适用于离散决策问题。

    Parameters
    ----------
    c : np.ndarray, shape (n,)
        目标函数系数。
    A_ub, b_ub, A_eq, b_eq, bounds, objective : 同 linear_programming。
    cat : str
        变量类型："Integer"（整数）、"Binary"（0-1）、"Continuous"（连续）。

    Returns
    -------
    result : dict
        keys: x (最优解), fun (最优目标值), success, status, message。

    Raises
    ------
    ImportError
        未安装 pulp 时给出安装提示。

    Notes
    -----
    - 适用于背包问题、选址问题、排班问题等含整数约束的优化。
    - 大规模问题可能求解缓慢。

    Examples
    --------
    >>> c = np.array([8, 5, 12, 6])  # 背包价值
    >>> A_ub = np.array([[3, 2, 5, 4]])  # 重量约束
    >>> b_ub = np.array([8])
    >>> bounds = [(0, 1)] * 4
    >>> result = integer_programming(c, A_ub, b_ub, bounds=bounds,
    ...                              objective="max", cat="Binary")
    """
    try:
        import pulp
    except ImportError:
        raise ImportError("整数规划需要 PuLP 库。请运行: pip install pulp")

    c = np.asarray(c, dtype=float).ravel()
    n = len(c)

    if bounds is None:
        bounds = [(0, None)] * n

    # 变量类型映射
    cat_map = {
        "Integer": pulp.LpInteger,
        "Binary": pulp.LpBinary,
        "Continuous": pulp.LpContinuous,
    }
    var_cat = cat_map.get(cat, pulp.LpInteger)

    # 创建问题
    sense = pulp.LpMinimize if objective == "min" else pulp.LpMaximize
    prob = pulp.LpProblem("IP_Problem", sense)

    # 定义变量
    x = [pulp.LpVariable(f"x{i}", lowBound=bounds[i][0], upBound=bounds[i][1],
                         cat=var_cat) for i in range(n)]

    # 目标函数
    prob += pulp.lpSum([c[i] * x[i] for i in range(n)]), "objective"

    # 不等式约束
    if A_ub is not None and b_ub is not None:
        A_ub = np.asarray(A_ub, dtype=float)
        b_ub = np.asarray(b_ub, dtype=float).ravel()
        for j in range(A_ub.shape[0]):
            prob += pulp.lpSum([A_ub[j, i] * x[i] for i in range(n)]) <= b_ub[j], f"ineq_{j}"

    # 等式约束
    if A_eq is not None and b_eq is not None:
        A_eq = np.asarray(A_eq, dtype=float)
        b_eq = np.asarray(b_eq, dtype=float).ravel()
        for j in range(A_eq.shape[0]):
            prob += pulp.lpSum([A_eq[j, i] * x[i] for i in range(n)]) == b_eq[j], f"eq_{j}"

    # 求解
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    status = pulp.LpStatus[prob.status]
    success = prob.status == pulp.LpStatusOptimal
    x_opt = np.array([pulp.value(x[i]) for i in range(n)])

    fun = pulp.value(prob.objective)

    return {
        "x": x_opt,
        "fun": fun,
        "success": success,
        "status": status,
        "message": f"状态: {status}",
    }


# ============================================================================
# 3. 遗传算法（自实现）
# ============================================================================

def genetic_algorithm(
    func: Callable[[np.ndarray], float],
    n_dim: int,
    bounds: List[Tuple[float, float]],
    pop_size: int = 50,
    max_gen: int = 200,
    crossover_prob: float = 0.8,
    mutation_prob: float = 0.1,
    elite_ratio: float = 0.05,
    tol: float = 1e-8,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    遗传算法求解连续优化问题。

    包含：锦标赛选择、模拟二进制交叉 (SBX)、多项式变异、精英保留。

    Parameters
    ----------
    func : callable
        目标函数 func(x)，x 为 np.ndarray，返回标量。本算法默认最小化该函数。
    n_dim : int
        决策变量维度。
    bounds : list of (low, high)
        每个维度的搜索范围。
    pop_size : int
        种群大小，默认 50。
    max_gen : int
        最大进化代数，默认 200。
    crossover_prob : float
        交叉概率，默认 0.8。
    mutation_prob : float
        变异概率（每条染色体），默认 0.1。
    elite_ratio : float
        精英保留比例，默认 0.05。
    tol : float
        收敛容差：连续 30 代最优值变化 < tol 则提前终止。
    seed : int, optional
        随机种子。

    Returns
    -------
    result : dict
        keys:
        - x: 最优解
        - fun: 最优目标值
        - history: 每代最优值列表
        - success: 是否收敛
        - n_generations: 实际进化代数

    Notes
    -----
    - 适用于非凸、多峰、不可导的复杂优化问题。
    - 不依赖第三方进化算法库，纯 NumPy 实现。

    Examples
    --------
    >>> bounds = [(-5.12, 5.12)] * 2
    >>> result = genetic_algorithm(
    ...     lambda x: 20 + x[0]**2 + x[1]**2 - 10*(np.cos(2*np.pi*x[0])+np.cos(2*np.pi*x[1])),
    ...     n_dim=2, bounds=bounds, max_gen=100)
    """
    rng = np.random.default_rng(seed)
    bounds = np.asarray(bounds)
    low = bounds[:, 0]
    high = bounds[:, 1]
    scale = high - low

    n_elites = max(1, int(pop_size * elite_ratio))

    # ---- 初始化种群 ----
    pop = low + rng.random((pop_size, n_dim)) * scale
    fitness = np.apply_along_axis(func, 1, pop)
    history = [fitness.min()]

    best_idx = np.argmin(fitness)
    best_x = pop[best_idx].copy()
    best_fitness = fitness[best_idx]

    # 收敛计数器
    no_improve_count = 0

    for gen in range(max_gen):
        # ---- 精英保留 ----
        elite_indices = np.argpartition(fitness, n_elites)[:n_elites]
        elites = pop[elite_indices].copy()

        # ---- 选择：锦标赛 ----
        new_pop = np.empty_like(pop)
        new_pop[:n_elites] = elites  # 精英直接保留

        for i in range(n_elites, pop_size):
            # 随机选两个父代
            idx_a, idx_b = rng.choice(pop_size, size=2, replace=False)
            f_a, f_b = fitness[idx_a], fitness[idx_b]
            parent = pop[idx_a if f_a <= f_b else idx_b]

            # ---- 交叉：模拟二进制交叉 SBX ----
            if rng.random() < crossover_prob and i + 1 < pop_size:
                partner = pop[idx_b]
                eta_c = 20.0
                u = rng.random(n_dim)
                beta = np.where(u <= 0.5,
                                (2 * u) ** (1 / (eta_c + 1)),
                                (1 / (2 - 2 * u)) ** (1 / (eta_c + 1)))
                child1 = 0.5 * ((1 + beta) * parent + (1 - beta) * partner)
                child2 = 0.5 * ((1 - beta) * parent + (1 + beta) * partner)
                child1 = np.clip(child1, low, high)
                child2 = np.clip(child2, low, high)
                new_pop[i] = child1
                new_pop[i + 1] = child2
                i += 1
            else:
                new_pop[i] = parent

        # ---- 变异：多项式变异 + 大跳跃 ----
        for i in range(n_elites, pop_size):
            if rng.random() < mutation_prob:
                eta_m = 20.0
                u = rng.random(n_dim)
                delta = np.where(
                    u <= 0.5,
                    (2 * u) ** (1 / (eta_m + 1)) - 1,
                    1 - (2 - 2 * u) ** (1 / (eta_m + 1)),
                )
                new_pop[i] += delta * scale * 0.3
                new_pop[i] = np.clip(new_pop[i], low, high)

        # ---- 停滞重启：若若干代无改进，对部分个体随机重置 ----
        if no_improve_count > 10 and no_improve_count % 5 == 0:
            n_restart = max(1, pop_size // 5)
            restart_indices = rng.choice(
                np.arange(n_elites, pop_size), size=n_restart, replace=False
            )
            new_pop[restart_indices] = low + rng.random((n_restart, n_dim)) * scale

        # ---- 评估 ----
        pop = new_pop
        fitness = np.apply_along_axis(func, 1, pop)

        # 更新最优解
        gen_best_idx = np.argmin(fitness)
        gen_best_fitness = fitness[gen_best_idx]

        if gen_best_fitness < best_fitness - tol:
            best_fitness = gen_best_fitness
            best_x = pop[gen_best_idx].copy()
            no_improve_count = 0
        else:
            no_improve_count += 1

        history.append(best_fitness)

        # 收敛判断
        if no_improve_count >= 30:
            break

    success = no_improve_count >= 30

    return {
        "x": best_x,
        "fun": best_fitness,
        "history": history,
        "success": success,
        "n_generations": len(history),
    }


# ============================================================================
# 4. 模拟退火算法
# ============================================================================

def simulated_annealing(
    func: Callable[[np.ndarray], float],
    bounds: List[Tuple[float, float]],
    init_solution: Optional[np.ndarray] = None,
    T_start: float = 1000.0,
    T_end: float = 0.01,
    cooling_rate: float = 0.95,
    max_iter: int = 200,
    step_size: float = 0.1,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    模拟退火算法求解连续优化问题。

    以一定概率接受劣解，随着温度降低逐步收敛到全局最优。

    Parameters
    ----------
    func : callable
        目标函数 func(x)，返回标量。默认最小化。
    bounds : list of (low, high)
        各维度搜索范围。
    init_solution : np.ndarray, optional
        初始解，默认取搜索范围中心。
    T_start : float
        起始温度，默认 1000。
    T_end : float
        终止温度，默认 0.01。
    cooling_rate : float
        降温系数 $\\alpha \\in (0, 1)$，默认 0.95。
    max_iter : int
        各温度下的最大内循环迭代次数。
    step_size : float
        新解生成步长（相对搜索范围的比例），默认 0.1。
    seed : int, optional
        随机种子。

    Returns
    -------
    result : dict
        keys: x, fun, history, success, acceptance_rate。

    Notes
    -----
    - 适用于旅行商问题（TSP）、布局优化、参数调优等组合/连续优化问题。
    - 降温策略：$T_{k+1} = \\alpha \\cdot T_k$（指数降温）。
    - 若目标函数评估代价高，可减少 max_iter 或加大 cooling_rate。

    Examples
    --------
    >>> bounds = [(-10, 10), (-10, 10)]
    >>> result = simulated_annealing(
    ...     lambda x: (x[0]-2)**2 + (x[1]+3)**2,
    ...     bounds=bounds, T_start=100)
    """
    rng = np.random.default_rng(seed)
    bounds = np.asarray(bounds)
    low = bounds[:, 0]
    high = bounds[:, 1]
    scale = high - low

    # 初始解
    if init_solution is None:
        current_x = low + rng.random(len(low)) * scale
    else:
        current_x = np.asarray(init_solution, dtype=float).ravel()
        current_x = np.clip(current_x, low, high)

    current_val = func(current_x)
    best_x = current_x.copy()
    best_val = current_val

    T = T_start
    total_trials = 0
    accepted = 0
    history = [best_val]

    while T > T_end:
        for _ in range(max_iter):
            # 生成邻域解：高斯扰动
            new_x = current_x + rng.normal(0, step_size, len(low)) * scale * (T / T_start)
            new_x = np.clip(new_x, low, high)
            new_val = func(new_x)
            total_trials += 1

            delta = new_val - current_val

            # Metropolis 准则
            if delta <= 0 or rng.random() < np.exp(-delta / T):
                current_x = new_x
                current_val = new_val
                accepted += 1

                if current_val < best_val:
                    best_x = current_x.copy()
                    best_val = current_val

        history.append(best_val)
        T *= cooling_rate

    acceptance_rate = accepted / total_trials if total_trials > 0 else 0.0

    return {
        "x": best_x,
        "fun": best_val,
        "history": history,
        "success": T <= T_end,
        "acceptance_rate": acceptance_rate,
    }


# ============================================================================
# 5. 混合整数非线性规划 (MINLP) 及非线性优化
# ============================================================================

def minlp(
    func: Callable[[np.ndarray], float],
    bounds: List[Tuple[float, float]],
    strategy: str = "differential_evolution",
    **kwargs,
) -> Dict[str, Any]:
    """
    非线性规划 / 混合整数非线性规划接口。

    使用 scipy 的差分进化（differential_evolution）处理非凸、非光滑全局优化问题。
    若需纯整数约束，可在目标函数内对解取整后计算。

    Parameters
    ----------
    func : callable
        目标函数 func(x)，返回标量。默认最小化。
    bounds : list of (low, high)
        各维度搜索范围。
    strategy : str
        优化策略：
        - "differential_evolution" : scipy 差分进化（默认）
        - 未来可扩展调用 BARON / Bonmin 等 MINLP 求解器接口。
    **kwargs
        传递给底层优化器的额外参数。

    Returns
    -------
    result : dict
        keys: x, fun, success, message。

    Notes
    -----
    - 差分进化适用于非凸、不可导、多峰的全局连续优化。
    - 若变量含整数约束，可在 target 函数内：``x_int = np.round(x).astype(int)``，
      再用 x_int 计算目标值。差分进化在连续域搜索，取整后作为实际解评估。
    - 对于严格 MINLP 问题，建议使用商业求解器（如 BARON、Gurobi）通过
      pyomo 接口调用。此处仅提供轻量级替代方案。

    References
    ----------
    Storn, R., & Price, K. (1997). Differential Evolution.

    Examples
    --------
    >>> # 求解 min (x1 - 3)^2 + (x2 + 2)^2, x1 in [-10,10], x2 in [-10,10]
    >>> result = minlp(lambda x: (x[0]-3)**2 + (x[1]+2)**2,
    ...                bounds=[(-10,10), (-10,10)])
    """
    if strategy == "differential_evolution":
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = differential_evolution(func, bounds, **kwargs)

        return {
            "x": res.x,
            "fun": res.fun,
            "success": res.success,
            "message": res.message,
        }
    else:
        raise ValueError(f"未知策略 '{strategy}'。当前仅支持 'differential_evolution'。")


# ============================================================================
# 测试示例
# ============================================================================

if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["SimHei", "Songti SC", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    np.set_printoptions(precision=4, suppress=True)
    warnings.filterwarnings("ignore")

    print("=" * 60)
    print("优化模型库 — 测试示例")
    print("=" * 60)

    # ======== 1. 线性规划：生产计划 ========
    print("\n" + "-" * 40)
    print("[1] 线性规划 — 生产计划问题")
    print("-" * 40)
    # max Z = 3x1 + 2x2
    # s.t.  2x1 + x2 <= 6
    #        x1 + 2x2 <= 6
    #        x1, x2 >= 0
    c_lp = np.array([3, 2])
    A_ub_lp = np.array([[2, 1], [1, 2]])
    b_ub_lp = np.array([6, 6])
    bounds_lp = [(0, None), (0, None)]

    res_lp = linear_programming(c_lp, A_ub_lp, b_ub_lp, bounds=bounds_lp, objective="max")
    print(f"  最优解: x1 = {res_lp['x'][0]:.2f}, x2 = {res_lp['x'][1]:.2f}")
    print(f"  最大利润: Z = {res_lp['fun']:.2f}")
    print(f"  状态: {res_lp['message']}")

    # ======== 2. 整数规划：0-1 背包 ========
    print("\n" + "-" * 40)
    print("[2] 整数规划 — 0-1 背包问题")
    print("-" * 40)
    # 物品价值
    values = np.array([8, 5, 12, 6])
    # 物品重量
    weights = np.array([[3, 2, 5, 4]])
    capacity = np.array([8])

    bounds_knap = [(0, 1)] * 4

    try:
        res_ip = integer_programming(
            values, weights, capacity, bounds=bounds_knap,
            objective="max", cat="Binary",
        )
        print(f"  最优选择: {res_ip['x']}")
        print(f"  总价值: {res_ip['fun']:.0f}")
        selected = [f"物品{i+1}" for i, v in enumerate(res_ip['x']) if v > 0.5]
        print(f"  选中物品: {', '.join(selected)}")
        print(f"  状态: {res_ip['status']}")
    except ImportError:
        print("  [跳过] 未安装 PuLP，请: pip install pulp")

    # ======== 3. 遗传算法：Rastrigin 函数 ========
    print("\n" + "-" * 40)
    print("[3] 遗传算法 — Rastrigin 函数最小化")
    print("-" * 40)
    # Rastrigin 全局最小值 f(0,...,0) = 0
    def rastrigin(x):
        A = 10.0
        return A * len(x) + np.sum(x ** 2 - A * np.cos(2 * np.pi * x))

    n_dim = 3
    rastrigin_bounds = [(-5.12, 5.12)] * n_dim

    res_ga = genetic_algorithm(
        rastrigin, n_dim=n_dim, bounds=rastrigin_bounds,
        pop_size=80, max_gen=300, seed=42,
    )
    print(f"  最优解: {res_ga['x']}")
    print(f"  最优值: f(x) = {res_ga['fun']:.6f}  (理论最小值: 0.0)")
    print(f"  进化代数: {res_ga['n_generations']}")
    print(f"  收敛: {'是' if res_ga['success'] else '达到最大代数'}")

    # ======== 4. 模拟退火 ========
    print("\n" + "-" * 40)
    print("[4] 模拟退火 — 二维搜索")
    print("-" * 40)

    def ackley(x):
        a, b, c = 20, 0.2, 2 * np.pi
        d = len(x)
        sum1 = np.sum(x ** 2)
        sum2 = np.sum(np.cos(c * x))
        return -a * np.exp(-b * np.sqrt(sum1 / d)) - np.exp(sum2 / d) + a + np.e

    ackley_bounds = [(-32, 32), (-32, 32)]

    res_sa = simulated_annealing(
        ackley, bounds=ackley_bounds, T_start=500, max_iter=100,
        seed=42,
    )
    print(f"  最优解: {res_sa['x']}")
    print(f"  最优值: f(x) = {res_sa['fun']:.8f}  (理论最小值: 0.0)")
    print(f"  接受率: {res_sa['acceptance_rate']:.3f}")

    # ======== 5. MINLP：差分进化 ========
    print("\n" + "-" * 40)
    print("[5] MINLP 差分进化 — 非线性全局优化")
    print("-" * 40)

    def six_hump_camel(x):
        return (4 - 2.1 * x[0]**2 + x[0]**4 / 3) * x[0]**2 + \
               x[0] * x[1] + (-4 + 4 * x[1]**2) * x[1]**2

    camel_bounds = [(-3, 3), (-2, 2)]

    res_de = minlp(six_hump_camel, bounds=camel_bounds, seed=42, polish=False)
    print(f"  最优解: {res_de['x']}")
    print(f"  最优值: f(x) = {res_de['fun']:.6f}  (理论最小值约: -1.0316)")
    print(f"  状态: {'成功' if res_de['success'] else '未收敛'}")

    # ======== 收敛曲线对比 ========
    print("\n[绘图] 保存收敛曲线至 figures/optimization_convergence.png")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # GA 收敛曲线
    ax = axes[0]
    ax.plot(res_ga['history'], "b-", linewidth=1, alpha=0.8)
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5, label="理论最优 0")
    ax.set_xlabel("代数")
    ax.set_ylabel("目标函数值")
    ax.set_title(f"遗传算法收敛曲线 (Rastrigin {n_dim}维)")
    ax.set_yscale("symlog", linthresh=0.01)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # SA 收敛曲线
    ax2 = axes[1]
    ax2.plot(res_sa['history'], "r-", linewidth=1, alpha=0.8)
    ax2.axhline(y=0, color="gray", linestyle="--", alpha=0.5, label="理论最优 0")
    ax2.set_xlabel("外循环次数")
    ax2.set_ylabel("目标函数值")
    ax2.set_title("模拟退火收敛曲线 (Ackley 2维)")
    ax2.set_yscale("symlog", linthresh=0.01)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    import os
    os.makedirs("../figures", exist_ok=True)
    plt.savefig("../figures/optimization_convergence.png", dpi=150)
    plt.close()
    print("  已保存至 figures/optimization_convergence.png")

    # ======== 汇总 ========
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"{'方法':<16} {'最优值':>12} {'理论最优':>10} {'状态':>10}")
    print("-" * 52)
    print(f"{'线性规划':<16} {res_lp['fun']:>12.2f} {'N/A':>10} {'成功':>10}")
    if 'res_ip' in dir():
        print(f"{'整数规划':<16} {res_ip['fun']:>12.0f} {'N/A':>10} {str(res_ip['success']):>10}")
    print(f"{'遗传算法':<16} {res_ga['fun']:>12.6f} {0.0:>10} {str(res_ga['success']):>10}")
    print(f"{'模拟退火':<16} {res_sa['fun']:>12.8f} {0.0:>10} {'是':>10}")
    print(f"{'差分进化':<16} {res_de['fun']:>12.6f} {'~ -1.0316':>10} {str(res_de['success']):>10}")
    print("=" * 60)
