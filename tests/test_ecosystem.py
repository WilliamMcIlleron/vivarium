import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import rules.ecosystem as eco
from rules.ecosystem import Creature, World


def _flat_terrain():
    # Hand-constructed World() calls below bypass World.new()/from_dict(),
    # so terrain defaults to [] - unlike any real world, which always has a
    # full grid. An empty terrain silently breaks any code that indexes
    # terrain[y][x] without a length check, in a way that has nothing to do
    # with the logic under test.
    return ["g" * eco.GRID_SIZE for _ in range(eco.GRID_SIZE)]


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
    world = World(tick=0, creatures=[grazer, hunter], resources=[], terrain=_flat_terrain())
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


def test_new_world_has_full_terrain_grid():
    world = World.new()
    assert len(world.terrain) == 40
    assert all(len(row) == 40 for row in world.terrain)
    assert all(ch in "wsgf" for row in world.terrain for ch in row)


def test_terrain_persists_through_serialization():
    world = World.new()
    data = world.to_dict()
    restored = World.from_dict(data)
    assert restored.terrain == world.terrain


def test_old_save_without_terrain_gets_one_generated():
    world = World.from_dict({"tick": 5, "creatures": [], "resources": []})
    assert len(world.terrain) == 40
    assert all(len(row) == 40 for row in world.terrain)


def test_old_save_without_traits_gets_empty_dict():
    world = World.from_dict({
        "tick": 5,
        "creatures": [
            {"id": "a", "x": 1, "y": 1, "energy": 30, "speed": 1, "sense_range": 5}
        ],
        "resources": [],
    })
    assert world.creatures[0].traits == {}
    assert world.creatures[0].trait("nonexistent") == 0.0


def test_traits_persist_through_serialization():
    world = World.new()
    world.creatures[0].traits = {"boldness": 0.7}
    data = world.to_dict()
    restored = World.from_dict(data)
    assert restored.creatures[0].traits == {"boldness": 0.7}


def test_extinct_grazers_can_migrate_back(monkeypatch):
    # Without this, a wiped-out grazer population is permanent - hunters
    # only eat grazers, never resources, so they'd starve out too with
    # nothing left to bring either species back.
    monkeypatch.setattr(eco, "GRAZER_MIGRATION_RATE", 1.0)  # force it for the test
    hunter = Creature(id="h1", x=0, y=0, energy=50, speed=1, sense_range=5, species="hunter")
    world = World(tick=0, creatures=[hunter], resources=[], terrain=_flat_terrain())
    world.step()
    assert any(c.species == "grazer" for c in world.creatures)


def test_registered_trait_spawns_with_default_and_mutates_in_bounds(monkeypatch):
    # TRAIT_REGISTRY is empty by design (framework, not content) - simulate
    # evolve having added a trait, and verify the generic machinery handles
    # it correctly without any trait-specific code.
    monkeypatch.setitem(eco.TRAIT_REGISTRY, "boldness", (0.5, 0.1, 0.0, 1.0))

    creature = eco._spawn_creature("grazer")
    assert creature.trait("boldness") == 0.5

    for _ in range(200):
        child = eco._reproduce(creature)
        assert 0.0 <= child.trait("boldness") <= 1.0
        creature = child
