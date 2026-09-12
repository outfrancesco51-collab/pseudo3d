import yaml

from MapGenerator import MapGenerator


class CircuitParser:

    OBJECT_DEFAULTS = {
        "step": 1.0,
        "offset": 0.0,
        "x": 0.0,
        "random_x": 0.0,
        "random_step": 0.0,
        "profile": None,
        "collidable": True,
        "anim": False,
        "frametime": 0.1,
    }

    def __init__(self, context, curve_right, curve_left, curve_hard_right, curve_hard_left, hill, down, profiles=None):
        self.context = context

        self.curve_right = curve_right
        self.curve_left = curve_left
        self.curve_hard_right = curve_hard_right
        self.curve_hard_left = curve_hard_left
        self.hill = hill
        self.down = down

        self.profiles = profiles if profiles is not None else {}

        self.objects = []
        self.checkpoints = []

        self.commands = {
            "CR": self.command_road,
            "CL": self.command_road,
            "CHR": self.command_road,
            "CHL": self.command_road,
            "H": self.command_road,
            "D": self.command_road,
            "S": self.command_road,
            "O": self.command_object,
            "V": self.command_vegetation,
            "F": self.command_forest,
            "MK": self.command_mark,
            "CHK": self.command_checkpoint,
            "BMP": self.command_bumps,
            "merge": self.command_merge,
            "E": self.command_enemy
        }

        self.last_segment=0
        self.current_tramo=None

    # ============================================================
    # LOAD
    # ============================================================

    def load(self, filename):
        with open(filename, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            raise ValueError("Empty circuit file")

        if "circuit" not in data:
            raise ValueError("Missing 'circuit' section")

        circuit = data["circuit"]

        sections = circuit.get("sections")

        if sections is None:
            raise ValueError("Missing 'sections'")

        for section in sections:
            self.parse_section(section)

        self.context.objects = self.objects
        self.context.checkpoints = self.checkpoints

    # ============================================================
    # SECTION
    # ============================================================

    def parse_section(self, section):
        name = section.get("name", "unnamed")

        print(f"Parsing section: {name}")

        commands = section.get("data", [])

        for command in commands:
            self.parse_command(command)

    # ============================================================
    # COMMAND
    # ============================================================

    def parse_command(self, command):
        if not isinstance(command, dict):
            raise ValueError(
                f"Invalid command: {command}"
            )

        cmd = command.get("command")

        if cmd is None:
            raise ValueError(
                f"Command without 'command': {command}"
            )

        handler = self.commands.get(cmd)

        if handler is None:
            raise ValueError(
                f"Unknown circuit command '{cmd}'"
            )

        handler(command)

    # ============================================================
    # UTILITIES
    # ============================================================

    def get_segments(self, command):
        segments = command.get("segments")
        if segments is not None:
            if not isinstance(segments, int) or isinstance(segments, bool):
                raise ValueError(
                    f"'segments' must be a positive integer: {segments}"
                )
            if segments <= 0:
                raise ValueError(
                    f"'segments' must be a positive integer: {segments}"
                )

        return segments

    def get_current_tramo(self, segments):
        if segments is None:
            if not self.current_tramo:
                raise ValueError(
                    "This command requires a previous road section "
                    "when 'segments' is omitted"
                )
            return self.current_tramo
        first_segment=self.last_segment+1
        if first_segment+segments > len(self.context.road.segments):
            raise ValueError(
                f"Requested {segments} segments, "
                f"but only {len(self.context.road.segments)-self.last_segment} exist"
            )

        last_segment=first_segment+segments
        return self.context.road.segments[first_segment:last_segment]

    # ============================================================
    # CR, CL, CHR, CHL
    # ============================================================

    def command_road(self, data):

        self.last_segment=len(self.context.road.segments)-1

        start = self.last_segment+1

        pattern = self.parse_pattern(data)

        self.context.road.add(pattern)

        self.current_tramo = self.context.road.segments[start:]

    # ============================================================
    # O
    # ============================================================

    def command_object(self, command):
        segments = self.get_segments(command)

        image = command.get("img")

        if image is None:
            raise ValueError(
                "Command 'O' requires 'img'"
            )

        tramo = self.get_current_tramo(segments)

        params = {}

        for key, default in self.OBJECT_DEFAULTS.items():
            value = command.get(key, default)

            # Resolver profile desde YAML
            if key == "profile" and value is not None:
                value = self.get_profile(value)

            params[key] = value

        self.objects = MapGenerator.objects(
            self.objects,
            tramo,
            image,
            **params
        )

    # ============================================================
    # V
    # ============================================================
    def command_vegetation(self, data):
        segments = self.get_segments(data)

        tramo = self.get_current_tramo(segments)

        img = data["img"]

        self.objects = self.context.vegetacion(
            self.objects,
            tramo,
            x=data.get("x", 2.0),
            step_x=data.get("step_x", 1.0),
            step_z=data.get("step_z", 5.0),
            offset_z=data.get("offset", 0.0),
            number=data.get("number", 1),
            objeto=img
        )
    # ============================================================
    # F
    # ============================================================
    def command_forest(self, data):
        segments = self.get_segments(data)

        tramo = self.get_current_tramo(segments)

        img = data["img"]

        self.objects = self.context.bosque(
            self.objects,
            tramo,
            x=data.get("x", 2.0),
            step_x=data.get("step_x", 1.0),
            step_z=data.get("step_z", 5.0),
            offset_z=data.get("offset", 0.0),
            number=data.get("number", 1),
            random_x=data.get("random_x", 0.0),
            random_step=data.get("random_step", 0.0),
            objeto=img
        )
    # ============================================================
    # MK
    # ============================================================
    def command_mark(self, data):


        img = data["img"]

        MapGenerator.addMark(
            self.current_tramo[data["segment"]],
            img,
            x=data.get("x", 0.0),
            z=data.get("z", 0.0),
            w=data.get("w", 1.0),
            h=data.get("h", 1.0)
        )
    # ============================================================
    # CHK
    # ============================================================
    def command_checkpoint(self, data):
        if not self.current_tramo:
            raise ValueError(
                "Command 'CHK' requires a previous road section"
            )

        segment = data.get("segment", 0)

        try:
            s = self.current_tramo[segment]
        except IndexError:
            raise ValueError(
                f"CHK segment index {segment} out of range "
                f"for current tramo ({len(self.current_tramo)} segments)"
            )

        z_rel = data.get("z", 0.25)
        time = data.get("time", 55.0)

        # Asset
        self.objects = MapGenerator.objects(
            self.objects,
            [s],
            "checkpoint",
            step=1.0,
            offset=0.5,
            x=1.3,
            profile=self.profiles["checkpoint"]
        )

        # Checkpoint
        MapGenerator.addCheckpoint(
            s,
            z_rel,
            time
        )

        # Indicador
        self.checkpoints.append(
            s.z + z_rel
        )
    # ============================================================
    # E
    # ============================================================
    def command_enemy(self, data):
        if not self.current_tramo:
            raise ValueError(
                "Command 'E' requires a previous road section"
            )

        segment = data.get("segment", 0)

        try:
            s = self.current_tramo[segment]
        except IndexError:
            raise ValueError(
                f"E segment index {segment} out of range "
                f"for current tramo ({len(self.current_tramo)} segments)"
            )

        z_rel = data.get("z", 0.0)
        x_rel = data.get("x_rel", 0.0)
        speed = data.get("speed", 10.0)

        # Enemy
        MapGenerator.addEnemy(
            s,
            z_rel,
            x_rel,
            speed
        )

    # ============================================================
    # BMP
    # ============================================================
    def command_bumps(self, data):
        repeats = data.get("repeats", 3)
        segments = data.get("segments", 4)
        slope = data.get("slope", 0.025)

        if repeats <= 0:
            raise ValueError(
                f"Invalid BMP repeats: {repeats}"
            )

        if segments <= 0:
            raise ValueError(
                f"Invalid BMP segments: {segments}"
            )

        self.last_segment=len(self.context.road.segments)-1

        start = self.last_segment+1

        self.context.add_bumps(
            repeats=repeats,
            segments=segments,
            slope=slope
        )

        self.current_tramo = self.context.road.segments[start:]
    # ============================================================
    # PROFILE
    # ============================================================

    def get_profile(self, name):
        if not isinstance(name, str):
            raise ValueError(
                f"Profile must be a string in YAML: {name}"
            )

        if name not in self.profiles:
            raise ValueError(
                f"Unknown profile '{name}'"
            )

        return self.profiles[name]



    def parse_pattern(self, data):

        command = data.get("command")

        if command is None:
            raise ValueError("Pattern without 'command'")

        segments = data.get("segments")

        if segments is None:
            raise ValueError(
                f"Pattern '{command}' requires 'segments'"
            )

        if command == "S":
            return MapGenerator.pattern(
                MapGenerator.NONE,
                0.0,
                segments
            )

        if command == "CR":
            return MapGenerator.pattern(
                MapGenerator.CURVE,
                self.curve_right,
                segments
            )

        if command == "CL":
            return MapGenerator.pattern(
                MapGenerator.CURVE,
                self.curve_left,
                segments
            )

        if command == "H":
            return MapGenerator.pattern(
                MapGenerator.HILL,
                self.hill,
                segments
            )

        if command == "D":
            return MapGenerator.pattern(
                MapGenerator.HILL,
                self.down,
                segments
            )

        if command == "CHR":
            return MapGenerator.pattern(
                MapGenerator.CURVE,
                self.curve_hard_right,
                segments
            )

        if command == "CHL":
            return MapGenerator.pattern(
                MapGenerator.CURVE,
                self.curve_hard_left,
                segments
            )

        raise ValueError(
            f"Unknown pattern command '{command}'"
        )

    def command_merge(self, data):

        op1 = data.get("op1")
        op2 = data.get("op2")

        if op1 is None or op2 is None:
            raise ValueError(
                "Command 'merge' requires 'op1' and 'op2'"
            )

        pattern1 = self.parse_pattern(op1)
        pattern2 = self.parse_pattern(op2)

        self.last_segment=len(self.context.road.segments)-1

        start = self.last_segment+1

        self.context.road.add(
            MapGenerator.merge(
                pattern1,
                pattern2
            )
        )

        self.current_tramo = self.context.road.segments[start:]

