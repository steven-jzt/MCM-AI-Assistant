"""
微分方程数值解模块 — differential.py
======================================
包含 ODE 求解器（scipy / 欧拉 / RK4）、一维热传导方程有限差分。
用于数学建模竞赛中的动力系统模拟与偏微分方程数值求解。
"""

import warnings
from typing import Tuple, Optional, Callable, List, Union

import numpy as np
import pandas as pd


# ============================================================================
# 通用：中文绘图设置
# ============================================================================

def _set_chinese_font():
    import matplotlib.pyplot as plt
    for font in ["SimHei", "Songti SC", "Microsoft YaHei", "WenQuanYi Micro Hei", "DejaVu Sans"]:
        try:
            plt.rcParams["font.sans-serif"] = [font]
            plt.rcParams["axes.unicode_minus"] = False
            return
        except Exception:
            continue


# ============================================================================
# 1. 封装 solve_ivp
# ============================================================================

def solve_ode(
    fun: Callable[[float, np.ndarray], np.ndarray],
    t_span: Tuple[float, float],
    y0: Union[List, np.ndarray],
    method: str = "RK45",
    max_step: float = np.inf,
    rtol: float = 1e-3,
    atol: float = 1e-6,
    dense_output: bool = False,
    t_eval: Optional[np.ndarray] = None,
) -> dict:
    """
    常微分方程（ODE）数值求解器，封装 scipy.integrate.solve_ivp。

    求解初值问题：$dy/dt = f(t, y)$, $y(t_0) = y_0$。

    Parameters
    ----------
    fun : callable
        右端函数 fun(t, y)，t 为标量，y 为 shape (n,) 的 numpy 数组，返回同形状数组。
    t_span : tuple (t0, tf)
        时间区间。
    y0 : list or np.ndarray
        初始值向量。
    method : str
        求解方法：
        - "RK45" : 默认，显式 Runge-Kutta 5(4)，适合非刚性方程
        - "RK23" : 显式 Runge-Kutta 3(2)
        - "DOP853" : 显式 8 阶，高精度需求
        - "Radau" : 隐式 Runge-Kutta，适合刚性方程
        - "BDF" : 向后差分公式，适合刚性方程
        - "LSODA" : 自动切换刚性/非刚性
    max_step : float
        最大步长限制。
    rtol : float
        相对容差。
    atol : float
        绝对容差。
    dense_output : bool
        是否返回插值函数，默认 False。
    t_eval : np.ndarray, optional
        指定的输出时间点。若为 None，由求解器自适应选点。

    Returns
    -------
    result : dict
        keys:
        - t : 时间点数组
        - y : 解数组 shape (n_vars, n_times)
        - success : 是否积分成功
        - message : 状态信息
        - nfev : 函数评估次数
        - sol : 插值函数（仅 dense_output=True 时）

    Notes
    -----
    - 若求解失败，尝试减小 max_step 或放大 rtol/atol。
    - 刚性方程（如化学反应）请使用 method="Radau" 或 "BDF"。

    Examples
    --------
    >>> def exp_ode(t, y): return -0.5 * y   # dy/dt = -0.5y
    >>> res = solve_ode(exp_ode, (0, 10), [1.0])
    >>> print(f"y(10) = {res['y'][0, -1]:.4f}")
    """
    from scipy.integrate import solve_ivp

    y0 = np.asarray(y0, dtype=float).ravel()

    res = solve_ivp(
        fun, t_span, y0, method=method, max_step=max_step,
        rtol=rtol, atol=atol, dense_output=dense_output,
        t_eval=t_eval,
    )

    return {
        "t": res.t,
        "y": res.y,
        "success": res.success,
        "message": res.message,
        "nfev": res.nfev,
        "sol": res.sol if dense_output else None,
    }


# ============================================================================
# 2. 一维热传导方程（显式有限差分）
# ============================================================================

def heat_equation_1d(
    length: float,
    total_time: float,
    nx: int,
    nt: int,
    alpha: float,
    initial_condition: Callable[[np.ndarray], np.ndarray],
    boundary_conditions: Tuple[str, str] = ("dirichlet", "dirichlet"),
    boundary_values: Tuple[float, float] = (0.0, 0.0),
) -> dict:
    """
    一维热传导方程有限差分求解（FTCS 显式格式）。

    求解：$\\partial u/\\partial t = \\alpha \\partial^2 u/\\partial x^2$,
    $x \\in [0, L]$, $t \\in [0, T]$。

    Parameters
    ----------
    length : float
        杆长度 L。
    total_time : float
        模拟总时间 T。
    nx : int
        空间网格点数（含两端点）。
    nt : int
        时间步数。
    alpha : float
        热扩散系数，$\\alpha > 0$。
    initial_condition : callable
        初始温度分布 u(x, 0) = f(x)，输入 x 网格数组，返回 u 值数组。
    boundary_conditions : tuple of str
        左右边界条件类型：
        - "dirichlet" : 固定温度
        - "neumann" : 绝热边界（一阶导数为 0，默认实现）
    boundary_values : tuple of (float, float)
        左、右边界固定温度值（仅 Dirichlet 边界生效）。

    Returns
    -------
    result : dict
        keys:
        - x : 空间网格
        - t : 时间网格
        - u : 解矩阵 shape (nt+1, nx)
        - stable : 是否满足稳定性条件
        - dt : 时间步长
        - dx : 空间步长

    Raises
    ------
    ValueError
        若不满足稳定性条件且用户未处理。

    Notes
    -----
    - 傅里叶稳定性条件：$F = \\alpha \\Delta t / (\\Delta x)^2 \\le 0.5$。
      若 F > 0.5，发出警告但不终止——求解可能发散。
    - 空间二阶中心差分，时间一阶前向差分。
    - 使用场景：热传导、扩散过程、污染物扩散等。

    Examples
    --------
    >>> def init(x): return np.sin(np.pi * x / 1.0)  # 正弦初始温度
    >>> res = heat_equation_1d(1.0, 0.1, nx=50, nt=500, alpha=0.01,
    ...                        initial_condition=init)
    >>> print(f"稳定性因子 F = {res['stable']}")
    """
    # 网格
    dx = length / (nx - 1)
    dt = total_time / nt
    x = np.linspace(0, length, nx)
    t = np.linspace(0, total_time, nt + 1)

    # 稳定性检查（Fourier 数）
    F = alpha * dt / (dx ** 2)
    is_stable = F <= 0.5
    if not is_stable:
        warnings.warn(
            f"稳定性条件不满足：F = {F:.4f} > 0.5。"
            f"建议增加 nx 或增大 dt（减少 nt）。"
            f"当前 dx = {dx:.6f}, dt = {dt:.6f}。",
            UserWarning,
        )
    else:
        print(f"[热传导] 稳定性条件满足：F = {F:.4f} <= 0.5")

    # 初始化解矩阵
    u = np.zeros((nt + 1, nx))
    u[0, :] = initial_condition(x)

    bc_left, bc_right = boundary_conditions

    # 时间推进
    for n in range(nt):
        # 内部点：FTCS 格式
        u[n + 1, 1:-1] = u[n, 1:-1] + F * (
            u[n, 2:] - 2 * u[n, 1:-1] + u[n, :-2]
        )

        # 左边界
        if bc_left == "dirichlet":
            u[n + 1, 0] = boundary_values[0]
        elif bc_left == "neumann":
            u[n + 1, 0] = u[n + 1, 1]  # 一阶前向差分近似 u_x = 0
        else:
            raise ValueError(f"未知边界条件: {bc_left}")

        # 右边界
        if bc_right == "dirichlet":
            u[n + 1, -1] = boundary_values[1]
        elif bc_right == "neumann":
            u[n + 1, -1] = u[n + 1, -2]
        else:
            raise ValueError(f"未知边界条件: {bc_right}")

    return {
        "x": x,
        "t": t,
        "u": u,
        "stable": F,
        "dt": dt,
        "dx": dx,
    }


# ============================================================================
# 3. 显式欧拉法
# ============================================================================

def euler_method(
    fun: Callable[[float, np.ndarray], np.ndarray],
    t_span: Tuple[float, float],
    y0: Union[List, np.ndarray],
    h: float,
) -> dict:
    """
    显式欧拉法求解常微分方程初值问题。

    一阶精度，适用于教学演示和简单方程验证。

    Parameters
    ----------
    fun : callable
        右端函数 fun(t, y)，返回 dy/dt。
    t_span : tuple (t0, tf)
        时间区间。
    y0 : list or np.ndarray
        初始值。
    h : float
        固定步长。

    Returns
    -------
    result : dict
        keys: t (时间点), y (解数组 shape (n_vars, n_steps))。

    Notes
    -----
    - 公式：$y_{n+1} = y_n + h \\cdot f(t_n, y_n)$。
    - 局部截断误差 $O(h^2)$，全局误差 $O(h)$。
    - 步长 h 过大可能导致数值不稳定，建议先试探性测试。

    Examples
    --------
    >>> def exp_decay(t, y): return -0.5 * y
    >>> res = euler_method(exp_decay, (0, 5), [1.0], h=0.1)
    >>> print(f"y(5) = {res['y'][0, -1]:.4f}")
    """
    y0 = np.asarray(y0, dtype=float).ravel()
    t0, tf = t_span

    n_steps = int(np.ceil((tf - t0) / h))
    h_actual = (tf - t0) / n_steps

    t = np.linspace(t0, tf, n_steps + 1)
    y = np.zeros((len(y0), n_steps + 1))
    y[:, 0] = y0

    for i in range(n_steps):
        y[:, i + 1] = y[:, i] + h_actual * fun(t[i], y[:, i])

    return {"t": t, "y": y}


# ============================================================================
# 4. 四阶龙格-库塔法 (RK4)
# ============================================================================

def runge_kutta4(
    fun: Callable[[float, np.ndarray], np.ndarray],
    t_span: Tuple[float, float],
    y0: Union[List, np.ndarray],
    h: float,
) -> dict:
    """
    四阶龙格-库塔法（RK4）求解常微分方程。

    经典显式方法，四阶全局精度，不依赖 scipy 即可获得较高精度。

    Parameters
    ----------
    fun : callable
        右端函数 fun(t, y)，返回 dy/dt。
    t_span : tuple (t0, tf)
        时间区间。
    y0 : list or np.ndarray
        初始值向量。
    h : float
        固定步长。

    Returns
    -------
    result : dict
        keys: t (时间点), y (解数组 shape (n_vars, n_steps))。

    Notes
    -----
    - 公式：
        $k_1 = f(t_n, y_n)$
        $k_2 = f(t_n + h/2, y_n + h k_1/2)$
        $k_3 = f(t_n + h/2, y_n + h k_2/2)$
        $k_4 = f(t_n + h, y_n + h k_3)$
        $y_{n+1} = y_n + h(k_1 + 2k_2 + 2k_3 + k_4)/6$
    - 局部截断误差 $O(h^5)$，全局误差 $O(h^4)$。
    - 相比欧拉法，相同步长下精度高数个数量级。

    Examples
    --------
    >>> def exp_decay(t, y): return -0.5 * y
    >>> res = runge_kutta4(exp_decay, (0, 5), [1.0], h=0.5)
    >>> print(f"y(5) = {res['y'][0, -1]:.6f}")
    """
    y0 = np.asarray(y0, dtype=float).ravel()
    t0, tf = t_span

    n_steps = int(np.ceil((tf - t0) / h))
    h_actual = (tf - t0) / n_steps

    t = np.linspace(t0, tf, n_steps + 1)
    y = np.zeros((len(y0), n_steps + 1))
    y[:, 0] = y0

    for i in range(n_steps):
        ti = t[i]
        yi = y[:, i]

        k1 = fun(ti, yi)
        k2 = fun(ti + h_actual / 2, yi + h_actual * k1 / 2)
        k3 = fun(ti + h_actual / 2, yi + h_actual * k2 / 2)
        k4 = fun(ti + h_actual, yi + h_actual * k3)

        y[:, i + 1] = yi + h_actual * (k1 + 2 * k2 + 2 * k3 + k4) / 6

    return {"t": t, "y": y}


# ============================================================================
# 测试示例
# ============================================================================

if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _set_chinese_font()
    np.set_printoptions(precision=4, suppress=True)
    warnings.filterwarnings("ignore")

    print("=" * 60)
    print("微分方程数值解模块 — 测试示例")
    print("=" * 60)

    # ======== 1. 指数衰减：对比欧拉 / RK4 / solve_ivp ========
    print("\n" + "-" * 40)
    print("[1] ODE 求解器对比 — dy/dt = -0.5y, y(0)=1")
    print("-" * 40)

    def exp_decay(t, y):
        return -0.5 * y

    t_span = (0.0, 10.0)
    y0 = [1.0]
    y_exact = lambda t: np.exp(-0.5 * t)

    # 用三种方法求解
    res_scipy = solve_ode(exp_decay, t_span, y0, method="RK45")
    res_euler = euler_method(exp_decay, t_span, y0, h=0.2)
    res_rk4 = runge_kutta4(exp_decay, t_span, y0, h=0.5)

    print(f"  scipy (RK45): y(10) = {res_scipy['y'][0, -1]:.8f}  (精确: {y_exact(10):.8f})")
    print(f"  欧拉法:       y(10) = {res_euler['y'][0, -1]:.8f}  (h=0.2)")
    print(f"  RK4:          y(10) = {res_rk4['y'][0, -1]:.8f}  (h=0.5)")

    # ======== 2. 洛伦兹系统 ========
    print("\n" + "-" * 40)
    print("[2] 洛伦兹系统 (Lorenz Attractor)")
    print("-" * 40)

    def lorenz(t, state, sigma=10.0, rho=28.0, beta=8.0 / 3):
        x, y, z = state
        return np.array([sigma * (y - x), x * (rho - z) - y, x * y - beta * z])

    res_lorenz = solve_ode(lorenz, (0, 40), [1.0, 1.0, 1.0],
                           method="RK45", max_step=0.01)
    print(f"  积分步数: {len(res_lorenz['t'])}")
    print(f"  终点: x = {res_lorenz['y'][0, -1]:.4f}")
    print(f"       y = {res_lorenz['y'][1, -1]:.4f}")
    print(f"       z = {res_lorenz['y'][2, -1]:.4f}")

    # ======== 3. 一维热传导方程 ========
    print("\n" + "-" * 40)
    print("[3] 一维热传导方程")
    print("-" * 40)

    L = 1.0
    T = 0.5
    nx = 50
    nt = 2000
    alpha = 0.01

    # 初始条件：中心高温脉冲
    def init_pulse(x):
        return np.exp(-200 * (x - 0.5) ** 2)

    res_heat = heat_equation_1d(L, T, nx=nx, nt=nt, alpha=alpha,
                                initial_condition=init_pulse)

    print(f"  dx = {res_heat['dx']:.4f}, dt = {res_heat['dt']:.4f}")
    print(f"  t=0:   u_max = {res_heat['u'][0].max():.4f}")
    print(f"  t=T:   u_max = {res_heat['u'][-1].max():.4f}")
    print(f"  t=T:   u(0.5) = {res_heat['u'][-1, nx // 2]:.4f}")

    # ======== 4. 稳定性条件测试 ========
    print("\n" + "-" * 40)
    print("[4] 稳定性条件检查")
    print("-" * 40)

    # 故意用不稳定的参数
    try:
        res_unstable = heat_equation_1d(
            L, total_time=0.1, nx=20, nt=50, alpha=0.01,
            initial_condition=init_pulse,
        )
    except Exception as e:
        print(f"  {e}")

    # ======== 可视化 ========
    print("\n[绘图] 生成对比图 ...")

    fig, axes = plt.subplots(2, 2, figsize=(14, 11))

    # --- (a) ODE 方法对比 ---
    ax = axes[0, 0]
    t_exact = np.linspace(0, 10, 200)
    ax.plot(t_exact, y_exact(t_exact), "k-", linewidth=1.2, label="精确解")
    ax.plot(res_scipy["t"], res_scipy["y"][0], "b--", alpha=0.8, label="scipy RK45")
    ax.plot(res_euler["t"], res_euler["y"][0], "r:", alpha=0.8, label=f"欧拉 (h=0.2)")
    ax.plot(res_rk4["t"], res_rk4["y"][0], "g-.", alpha=0.8, label=f"RK4 (h=0.5)")
    ax.set_xlabel("t")
    ax.set_ylabel("y(t)")
    ax.set_title("指数衰减: 三种 ODE 方法对比")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    # --- (b) 洛伦兹吸引子 3D ---
    ax = axes[0, 1]
    from matplotlib.collections import LineCollection
    from mpl_toolkits.mplot3d import Axes3D

    # 用 subplot 转 3D
    fig.delaxes(ax)
    ax3d = fig.add_subplot(2, 2, 2, projection="3d")
    x_l, y_l, z_l = res_lorenz["y"]
    # 按时间着色
    n_pts = len(res_lorenz["t"])
    colors = plt.cm.viridis(np.linspace(0, 1, n_pts))
    for i in range(n_pts - 1):
        ax3d.plot(x_l[i:i+2], y_l[i:i+2], z_l[i:i+2],
                  color=colors[i], linewidth=0.4, alpha=0.7)
    ax3d.set_xlabel("X")
    ax3d.set_ylabel("Y")
    ax3d.set_zlabel("Z")
    ax3d.set_title("洛伦兹吸引子")

    # --- (c) 热传导: 不同时刻温度分布 ---
    ax = axes[1, 0]
    u_heat = res_heat["u"]
    x_heat = res_heat["x"]
    t_heat = res_heat["t"]
    # 选取几个时间切片
    slice_indices = [0, nt // 10, nt // 4, nt // 2, nt]
    for idx in slice_indices:
        ax.plot(x_heat, u_heat[idx], linewidth=1.2,
                label=f"t = {t_heat[idx]:.3f}")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("温度 u(x, t)")
    ax.set_title("一维热传导方程 (中心脉冲扩散)")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    # --- (d) 热传导 2D 伪彩色图 ---
    ax = axes[1, 1]
    X_mesh, T_mesh = np.meshgrid(x_heat, t_heat)
    im = ax.pcolormesh(X_mesh, T_mesh, u_heat, cmap="hot", shading="auto")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("t [s]")
    ax.set_title("温度场 u(x, t)")
    plt.colorbar(im, ax=ax, label="温度")

    plt.tight_layout()
    import os
    os.makedirs("../figures", exist_ok=True)
    plt.savefig("../figures/differential_demo.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  已保存至 figures/differential_demo.png")

    # ======== 汇总 ========
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    err_euler = abs(res_euler["y"][0, -1] - y_exact(10))
    err_rk4 = abs(res_rk4["y"][0, -1] - y_exact(10))
    print(f"  指数衰减精确解: y(10) = {y_exact(10):.8f}")
    print(f"  欧拉法误差:       {err_euler:.2e}  (h=0.2, {len(res_euler['t'])-1} 步)")
    print(f"  RK4 误差:        {err_rk4:.2e}  (h=0.5, {len(res_rk4['t'])-1} 步)")
    print(f"  洛伦兹积分步数:    {len(res_lorenz['t'])}")
    print(f"  热传导稳定性因子:  F = {res_heat['stable']:.4f}")
    print(f"  图表已保存至 figures/differential_demo.png")
    print("=" * 60)
