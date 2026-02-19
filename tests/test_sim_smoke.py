from microstructure_lab.sim.engine import SimulationConfig, Simulator
from microstructure_lab.sim.scenario import SyntheticScenario
from microstructure_lab.strategies.market_maker import InventorySkewMM


def test_simulation_smoke_runs():
    scenario = SyntheticScenario(
        seed=1,
        start_mid=100.0,
        tick_size=0.5,
        steps=100,
        sigma_bps=3.0,
        spread_ticks=2,
        depth_min=1.0,
        depth_max=5.0,
    )
    sim = Simulator(SimulationConfig())
    strategy = InventorySkewMM()

    result = sim.run(scenario.stream(), strategy)

    assert len(result.pnl_path) == 100
    assert len(result.inventory_path) == 100
    assert "final_pnl" in result.summary
