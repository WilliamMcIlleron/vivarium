import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rules.ecosystem import Creature, World


def test_new_world_has_starting_population():
    world = World.new()
    assert len(world.creatures) > 0
    assert world.tick == 0


def test_new_world_has_both_species():
    world = World.new()
    species = {c.species for c in world.creatures}
    assert species == {"grazer", "hunter"}


def test_old_save_without_species_defaults_to_grazer():
    # world.json saved before the predator/prey change has no "species" key.
    world = World.from_dict({
        "tick": 5,
        "creatures": [
            {"id": "a", "x": 1, "y": 1, "energy": 30, "speed": 1, "sense_range": 5}
        ],
        "resources": [],
    })
    assert world.creatures[0].species == "grazer"


def test_hunter_eats_colocated_grazer():
    hunter = Creature(id="h1", x=5, y=5, energy=50, speed=1, sense_range=5, species="hunter")
    grazer = Creature(id="g1", x=5, y=5, energy=50, speed=1, sense_range=5, species="grazer")
    world = World(tick=0, creatures=[grazer, hunter], resources=[])
    world.step()
    assert not any(c.id == "g1" for c in world.creatures)
    assert any(c.id == "h1" and c.energy > 50 for c in world.creatures)


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
