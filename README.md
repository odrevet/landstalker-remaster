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
python src/main.py -r 148 -x 320 -y 400 -z 128 --debug
```

* Load room 240 and set player location, enable debug

```
python src/main.py -r 240 -x 380 -y 120 -z 16 --debug
```

* Before falling to raft: Test fall warp and entity script

```
python src/main.py -r 159 -x 200 -y 600 -z 32 --debug
```

* Test entity placement, chests, tilemap culling

```
python src/main.py -r 153 -x 200 -y 100 -z 48 --debug
```

* Test crate

```
python src/main.py -r 157 -x 400 -y 300 -z 0 --debug
```

* Massan Inn (test map and register)

```
python src/main.py -r 598 -x 350 -y 210 -z 0 --debug
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
