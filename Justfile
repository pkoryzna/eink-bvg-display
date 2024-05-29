set shell := ["bash", "-xeEuo", "pipefail", "-c"]

# List available recipes
help:
    @just --list

install-deps:
    git submodule init
    git submodule update
    mpremote mip install requests functools
    mpremote fs --verbose cp ./deps/*.py :/

install:
    mpremote cp *.py config.json  :/

restart:
    mpremote reset
    mpremote exec "from soldered_inkplate6 import Inkplate; display = Inkplate(Inkplate.INKPLATE_1BIT); display.begin(); display.display()"
    mpremote exec --no-follow "import ui; ui.main()"
    mpremote

copy-fonts:
    mpremote cp --recursive fonts/ :
    
test-font:
    mpremote run experiments/fonttest.py

make-fonts:
    rm -f fonts/* || mkdir -p fonts/
    python font_maker.py --font "~/Library/Fonts/DIN1451_4H_08.87.ttf" --size 96 --filename fonts/regular.py
    python font_maker.py --font "OSP-DIN" --size 96 --filename fonts/condensed.py --extra-chars="ö:ö;ä:ä;ü:ü;Ö:Ö;Ä:Ä;Ü:Ü;ß:ß"