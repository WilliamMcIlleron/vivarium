import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rules.ecosystem import World


def test_new_world_has_starting_population():
    world = World.new()
    assert len(world.creatures) > 0
    assert world.tick == 0


def test_step_advances_tick():
    world = World.new()
    world.step()
    assert world.tick == 1


def test_step_does_not_crash_over_many_ticks():
    world = World.new()
    for _ in range(200):
        world.step()
    # No assertion on population size - extinction is a valid outcome,
    # a crash is not.


def test_roundtrip_serialization():
    world = World.new()
    world.step()
    data = world.to_dict()
    restored = World.from_dict(data)
    assert restored.tick == world.tick
    assert len(restored.creatures) == len(world.creatures)


def test_population_never_goes_negative():
    world = World.new()
    for _ in range(500):
        world.step()
        assert len(world.creatures) >= 0
