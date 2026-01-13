"""A very small text-adventure style demo.

This is not a full game engine; it's a minimal interactive REPL that:
- Seeds a demo database (if desired)
- Generates a play via Questrel
- Maps the generated play into a few navigable rooms
- Lets the user move around and perform classic parser actions

Design goals:
- Keep it tiny and understandable
- Show how Questrel output can drive a game loop
- Be deterministic when a seed is provided
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from questrel.api import generate_play_from_url
from questrel.logging import configure_logging, get_logger
from questrel.models.generated import GeneratedPlay
from questrel.models.request import GenerationRequest
from questrel.models.state import State
from questrel.random.deterministic import derive_seed, rng_from_seed
from questrel.runtime.branching import resolve_edges
from questrel.seed.demo_seed import seed_demo_db


logger = get_logger("demo.text_adventure")


@dataclass
class Room:
    key: str
    name: str
    description: str
    exits: dict[str, str] = field(default_factory=dict)
    characters: list[str] = field(default_factory=list)  # character_ids
    props: list[str] = field(default_factory=list)  # prop_ids


@dataclass
class Game:
    play: GeneratedPlay
    rooms: dict[str, Room]
    room_order: list[str]
    current_room: str
    inventory: list[str]
    state: State
    story_current_node_id: str
    story_step_index: int = 0
    # Lookups for nice rendering
    character_names: dict[str, str] = field(default_factory=dict)
    prop_names: dict[str, str] = field(default_factory=dict)
    location_names: dict[str, str] = field(default_factory=dict)

    def render_room(self) -> str:
        room = self.rooms[self.current_room]
        lines: list[str] = [f"{room.name}", room.description]

        if room.characters:
            lines.append("You see:")
            for cid in room.characters:
                lines.append(f"  - {self.character_names.get(cid, cid)}")

        if room.props:
            lines.append("On the ground:")
            for pid in room.props:
                lines.append(f"  - {self.prop_names.get(pid, pid)}")

        if room.exits:
            exits = ", ".join(sorted(room.exits.keys()))
            lines.append(f"Exits: {exits}")

        return "\n".join(lines)

    def render_story(self) -> str:
        node = _node_by_id(self.play, self.story_current_node_id)
        title = self.play.metadata.get("template_name") if self.play.metadata else None
        header = f"Story: {title}" if title else "Story"
        text = node.text or "(silence)"
        return f"{header}\n{text}"

    def help_text(self) -> str:
        return (
            "Commands:\n"
            "  movement: n,s,e,w,ne,nw,se,sw,u,d (or: go <dir>)\n"
            "  look | story | next | inv\n"
            "  get <item> | drop <item>\n"
            "  talk <person> | attack <person>\n"
            "  use <item> [on <target>] | give <item> to <person>\n"
            "  flags | help | quit\n"
        )

    def handle_command(self, raw: str) -> str:
        raw = raw.strip()
        if not raw:
            return ""

        cmd, *rest = raw.split()
        cmd = cmd.lower()
        args = " ".join(rest).strip()

        # Movement shortcuts
        if cmd in {"n", "s", "e", "w", "ne", "nw", "se", "sw", "u", "d"}:
            return self._move(cmd)
        if cmd == "go":
            if not args:
                return "Go where?"
            return self._move(args.lower())

        if cmd in {"look", "l"}:
            return self.render_room()
        if cmd in {"story"}:
            return self.render_story()
        if cmd in {"next", "continue"}:
            return self._advance_story()
        if cmd in {"inv", "inventory", "i"}:
            return self._render_inventory()
        if cmd in {"help", "?"}:
            return self.help_text()
        if cmd in {"quit", "exit"}:
            raise SystemExit(0)
        if cmd == "flags":
            return _render_flags(self.state.flags)

        if cmd in {"get", "take"}:
            if not args:
                return "Get what?"
            return self._get_item(args)
        if cmd == "drop":
            if not args:
                return "Drop what?"
            return self._drop_item(args)

        if cmd in {"talk", "speak"}:
            if not args:
                return "Talk to whom?"
            return self._talk(args)
        if cmd in {"attack", "hit"}:
            if not args:
                return "Attack whom?"
            return self._attack(args)

        if cmd == "use":
            if not args:
                return "Use what?"
            return self._use(args)
        if cmd == "give":
            if not args:
                return "Give what to whom?"
            return self._give(args)

        return "I don't understand that. Type 'help'."

    def _move(self, direction: str) -> str:
        room = self.rooms[self.current_room]
        nxt = room.exits.get(direction)
        if not nxt:
            return "You can't go that way."
        self.current_room = nxt
        return self.render_room()

    def _render_inventory(self) -> str:
        if not self.inventory:
            return "You are carrying nothing."
        lines = ["You are carrying:"]
        for pid in self.inventory:
            lines.append(f"  - {self.prop_names.get(pid, pid)}")
        return "\n".join(lines)

    def _get_item(self, query: str) -> str:
        room = self.rooms[self.current_room]
        pid = _match_id(query, room.props, self.prop_names)
        if not pid:
            return "You don't see that here."
        room.props.remove(pid)
        self.inventory.append(pid)
        self._apply_item_side_effects(pid)
        return f"Taken: {self.prop_names.get(pid, pid)}"

    def _drop_item(self, query: str) -> str:
        pid = _match_id(query, self.inventory, self.prop_names)
        if not pid:
            return "You aren't carrying that."
        self.inventory.remove(pid)
        self.rooms[self.current_room].props.append(pid)
        return f"Dropped: {self.prop_names.get(pid, pid)}"

    def _talk(self, query: str) -> str:
        room = self.rooms[self.current_room]
        cid = _match_id(query, room.characters, self.character_names)
        if not cid:
            return "No one by that name is here."

        name = self.character_names.get(cid, cid)
        self._apply_character_side_effects(cid, action="talk")
        return f"You talk to {name}. They seem busy, but you learn something."

    def _attack(self, query: str) -> str:
        room = self.rooms[self.current_room]
        cid = _match_id(query, room.characters, self.character_names)
        if not cid:
            return "No one by that name is here."
        name = self.character_names.get(cid, cid)
        self._apply_character_side_effects(cid, action="attack")
        return f"You attack {name}. The room erupts in chaos."

    def _use(self, args: str) -> str:
        # Very small parser: "use <item>" or "use <item> on <target>".
        item_part, _, target_part = args.partition(" on ")
        item_part = item_part.strip()
        target_part = target_part.strip()

        pid = _match_id(item_part, self.inventory, self.prop_names)
        if not pid:
            return "You aren't carrying that."

        self._apply_item_side_effects(pid)

        if target_part:
            return f"You use {self.prop_names.get(pid, pid)} on {target_part}."
        return f"You use {self.prop_names.get(pid, pid)}."

    def _give(self, args: str) -> str:
        # "give <item> to <person>"
        item_part, _, who_part = args.partition(" to ")
        item_part = item_part.strip()
        who_part = who_part.strip()

        pid = _match_id(item_part, self.inventory, self.prop_names)
        if not pid:
            return "You aren't carrying that."

        room = self.rooms[self.current_room]
        cid = _match_id(who_part, room.characters, self.character_names)
        if not cid:
            return "No one by that name is here."

        self.inventory.remove(pid)
        # we don't track NPC inventory; assume it is accepted
        self._apply_give_side_effects(pid, cid)
        return f"You give {self.prop_names.get(pid, pid)} to {self.character_names.get(cid, cid)}."

    def _advance_story(self) -> str:
        outgoing = [e for e in self.play.edges if e.from_node_id == self.story_current_node_id]
        if not outgoing:
            return "The story seems to be over."

        rng = rng_from_seed(derive_seed(self.play.seed, self.play.template_id, self.story_current_node_id, self.story_step_index))
        selected = resolve_edges(outgoing, state=self.state, strategy=_default_strategy(), rng=rng)
        self.story_step_index += 1

        if not selected:
            return "Nothing happens. (No valid choices.)"

        # Apply MULTI edges as additional narration, but only advance along the chosen SINGLE.
        multi = [e for e in selected if str(e.selection_mode).lower() == "selectionmode.multi" or str(e.selection_mode).lower() == "multi"]
        single = [e for e in selected if e not in multi]

        lines: list[str] = []
        for edge in multi:
            node = _node_by_id(self.play, edge.to_node_id)
            if node.text:
                lines.append(node.text)

        if single:
            self.story_current_node_id = single[0].to_node_id
            lines.append(self.render_story())
        else:
            lines.append("The story shifts, but you can't follow it.")

        return "\n".join(lines)

    def _apply_item_side_effects(self, prop_id: str) -> None:
        # Tiny hand-wavy hooks so player actions can affect branching.
        # This keeps the demo interesting without introducing a full rules engine.
        if prop_id.endswith("_key"):
            self.state.flags["has_key"] = True
        if prop_id.endswith("_scroll"):
            self.state.flags["magic"] = True
        if prop_id.endswith("_sword"):
            self.state.flags["brave"] = True

    def _apply_character_side_effects(self, char_id: str, *, action: str) -> None:
        if action == "talk" and char_id.endswith("_merchant"):
            self.state.flags["allow"] = True
        if action == "talk" and char_id.endswith("_mage"):
            self.state.flags["magic"] = True
        if action == "attack" and char_id.endswith("_villain"):
            self.state.flags["brave"] = True

    def _apply_give_side_effects(self, prop_id: str, char_id: str) -> None:
        if char_id.endswith("_merchant") and prop_id.endswith("_gem"):
            self.state.flags["allow"] = True


def _default_strategy():
    # Import lazily so demos don't affect core import paths.
    from questrel.models.enums import SingleSelectStrategy

    return SingleSelectStrategy.WEIGHTED


def _node_by_id(play: GeneratedPlay, node_id: str):
    for n in play.nodes:
        if n.node_id == node_id:
            return n
    raise KeyError(node_id)


def _guess_start_node_id(play: GeneratedPlay) -> str:
    # Heuristic: prefer node_id ending in "_start".
    for n in play.nodes:
        if n.node_id.endswith("_start"):
            return n.node_id
    # Fallback: stable order.
    return sorted(play.nodes, key=lambda x: x.node_id)[0].node_id


def _match_id(query: str, ids: list[str], names: dict[str, str]) -> str | None:
    q = query.strip().lower()
    if not q:
        return None
    # Exact match on id
    for i in ids:
        if i.lower() == q:
            return i
    # Substring match on display name
    for i in ids:
        n = names.get(i, i).lower()
        if q in n:
            return i
    return None


def _render_flags(flags: dict[str, Any]) -> str:
    if not flags:
        return "(no flags set)"
    lines = ["Flags:"]
    for k in sorted(flags.keys()):
        lines.append(f"  {k} = {flags[k]!r}")
    return "\n".join(lines)


def build_demo_rooms(play: GeneratedPlay) -> tuple[dict[str, Room], list[str]]:
    """Create a tiny map and place generated characters/props.

    Rooms are based on the generated locations if present; otherwise a default set.
    """

    # Use up to 4 rooms for a classic small text-adventure feel.
    locs = play.locations[:4]
    if not locs:
        locs = []

    room_order: list[str] = []
    rooms: dict[str, Room] = {}

    for idx, loc in enumerate(locs):
        key = loc.location_id
        room_order.append(key)
        rooms[key] = Room(
            key=key,
            name=loc.display_name,
            description=f"You are at {loc.display_name}.",
        )

    if not rooms:
        # Fallback rooms (should be rare because generator binds locations)
        for key, name in [("inn", "The Inn"), ("market", "The Market"), ("forest", "The Forest")]:
            room_order.append(key)
            rooms[key] = Room(key=key, name=name, description=f"You are at {name}.")

    # Wire a simple chain + a couple cross links
    for i, k in enumerate(room_order):
        if i + 1 < len(room_order):
            rooms[k].exits["e"] = room_order[i + 1]
            rooms[room_order[i + 1]].exits["w"] = k
    if len(room_order) >= 3:
        rooms[room_order[0]].exits["s"] = room_order[2]
        rooms[room_order[2]].exits["n"] = room_order[0]

    # Place characters/props round-robin
    for idx, ch in enumerate(play.characters):
        room_key = room_order[idx % len(room_order)]
        rooms[room_key].characters.append(ch.character_id)

    for idx, pr in enumerate(play.props):
        room_key = room_order[(idx + 1) % len(room_order)]
        rooms[room_key].props.append(pr.prop_id)

    return rooms, room_order


def build_game(*, play: GeneratedPlay, state: State) -> Game:
    rooms, order = build_demo_rooms(play)

    character_names = {c.character_id: c.display_name for c in play.characters}
    prop_names = {p.prop_id: p.display_name for p in play.props}
    location_names = {l.location_id: l.display_name for l in play.locations}

    start_room = order[0]
    start_node = _guess_start_node_id(play)

    return Game(
        play=play,
        rooms=rooms,
        room_order=order,
        current_room=start_room,
        inventory=[],
        state=state,
        story_current_node_id=start_node,
        character_names=character_names,
        prop_names=prop_names,
        location_names=location_names,
    )


async def generate_demo_play(
    *,
    db_url: str,
    seed: int,
    flags: dict[str, Any] | None = None,
    overwrite: bool = False,
    seed_db: bool = True,
) -> tuple[GeneratedPlay, State]:
    if overwrite:
        _maybe_delete_sqlite_file(db_url)
    if seed_db:
        await seed_demo_db(db_url)

    state = State(flags=flags or {})
    request = GenerationRequest(max_characters=3, location_count=3, prop_count=2, seed=None)
    play = await generate_play_from_url(db_url, request, state=state, seed=seed)
    return play, state


def _maybe_delete_sqlite_file(db_url: str) -> None:
    if not db_url.startswith("sqlite+"):
        return
    if ":///./" in db_url:
        filename = db_url.split(":///./", 1)[1]
        path = Path.cwd() / filename
        if path.exists():
            path.unlink()
        return
    if db_url.startswith("sqlite+aiosqlite:///"):
        # absolute/posix path form; best-effort
        filename = db_url.split("sqlite+aiosqlite:///", 1)[1]
        p = Path(filename)
        if p.exists():
            p.unlink()


async def run_repl(
    *,
    db_url: str = "sqlite+aiosqlite:///./questrel_demo.db",
    seed: int = 1,
    flags: dict[str, Any] | None = None,
    overwrite: bool = False,
    seed_db: bool = True,
    log_file: str = "questrel_text_adventure.log",
    no_log: bool = False,
) -> None:
    configure_logging(enabled=not no_log, log_file=log_file)

    play, state = await generate_demo_play(
        db_url=db_url,
        seed=seed,
        flags=flags,
        overwrite=overwrite,
        seed_db=seed_db,
    )

    game = build_game(play=play, state=state)

    print("Questrel Text Adventure Demo")
    print("----------------------------")
    if play.metadata:
        print(f"Generated template: {play.metadata.get('template_name')} ({play.metadata.get('template_key')})")
    print("Type 'help' for commands. Type 'next' to advance the story.")
    print("")

    print(game.render_room())
    print("")
    print(game.render_story())
    print("")

    while True:
        try:
            raw = input("> ")
            out = game.handle_command(raw)
            if out:
                print(out)
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return


def main() -> int:
    # Keep argument parsing minimal to avoid pulling in extra dependencies.
    # Use environment variables or edit defaults for more elaborate setups.
    asyncio.run(run_repl())
    return 0
