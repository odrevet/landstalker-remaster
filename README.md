# landstalker-py

A (stub) landstalker for PC, using assets from the megadrive game Landstalker exported using lordmir's landstalker_editor


# Needed assets

Export using https://github.com/lordmir/landstalker_editor/

**All assets goes under the `data` directory**

* `Rooms / export all rooms to tmx` and move them to `data/rooms`
* Select `Sprites / 000 Nigel` then `File / export sprite animation as png` and move `SpriteGfx000Anim001.png` png under `data/gfx`

# Python packages

```
source myenv/bin/activate
pip install -r requirements.txt
```

# Usage

--room or -r room number
--debug or -d enable debug mode
- x initial player x location
- y initial player y location
- z initial player z location


Uage examples:

* Load room 595

```
python src/main.py -r 595
```

* Game start location after intro

```
python src/main.py -r 148 -x 20 -y 25 -z 8 --debug
```

* Load room 240 and set player location, enable debug

```
python src/main.py -r 240 -x 23.75 -y 7.5 -z 1 --debug
```

* Before falling to raft: Test fall warp and entity script

```
python src/main.py -r 159 -x 12.5 -y 37.5 -z 2 --debug
```

* Test entity placement, chests, tilemap culling

```
python src/main.py -r 153 -x 12.5 -y 6.25 -z 3 --debug
```

* Test crate

```
python src/main.py -r 157 -x 25 -y 18 -z 0 --debug
```

* Massan Inn (test map and register)

```
python src/main.py -r 598 -x 19 -y 27 -z 8 --debug
```

* On raft

```
python src/main.py -r 168 -x 7 -y 9 -z 0.5 --debug
```

* Test boulder move

```
python src/main.py -r 5 -x 17 -y 19 -z 0
```

# Keys

* Arrowkeys: move hero.
* Ctrl-Left or Crtl-Right: load previous or next map
* Maj + Arrowkeys : move camera


# Debug mode

Display player coords in the HUD

F1: toogle draw boundbox 
F2: toogle draw heightmap
F3: toogle draw warp


# Standalone exec 

```
pyinstaller --onefile src/main.py \
    --name landstalker \
    --add-data "data:data" \
    --add-data "ui.json:."
```
