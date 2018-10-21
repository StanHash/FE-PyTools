Collection of python (3) tools for make/EA. Most tools output EA events.

# Usage

## `c2ea` & `n2c`

*See `NMM2CSV/README.md`.*

## `tmx2ea`

*See `TMX2EA/README.md`*

## `text-process`

```sh
(python3) "text-process.py" <input text> <output installer> <output definitions>
```

Note that, unlike for the original textprocess which generates `#incext`s, the output installer will `#incbin` a series of `xyz.fetxt.bin` files, but the program only generates `xyz.fetxt` files. It is your responsibility to ensure the `fetxt.bin` file is made from the `fetxt` file; such as by using a make rule involving a `ParseFile` invocation, perhaps. Ex:

```make
%.fetxt.bin: %.fetxt
	ParseFile $< -o $@
```

The idea is that you get the "list" of `fetxt.bin` files to generate through dependency analysis with Event Assembler. (I may add support for listing dependencies in text-process itself in the future).

## `portrait-process`

```sh
(python3) "portrait-process.py" <input list file> <output installer>
```

The input list file follows this format:

    <path to portrait png> <mug index> <mouth x> <mouth y> <eyes x> <eyes y> [mug index definition]
    ...

Empty lines and lines where the first character is `#` (comments) are ignored. You can therefore use a comment to remind you of the line format. Here's an example list file:

    #                       Index MouthX MouthY EyesX EyesY IndexDefinition
    "Portraits/Florina.png" 0x02  2      7      3     5     MUG_FLORINA

You can use quotes around parameters (as demonstrated above). This can be used to allow spaces in parameters (although I'd strongly recommend against that) or just to make the file nicer to read (this is very opinions).

[See here for a larger example](https://github.com/StanHash/VBA-MAKE/blob/master/Spritans/PortraitList.txt) (Lists all VBA portraits).

As for text-process, portrait-process doesn't generate any actual portrait data. It is your responsibility to make sure the files `<Portrait>_mug.dmp`, `<Portrait>_palette.dmp`, `<Portrait>_frames.dmp` and `<Portrait>_minimug.dmp` are generated from `<Portrait>.png`. Again, this is best done through a make rule involving a `PortraitFormatter` invocation:

```make
%_mug.dmp %_palette.dmp %_frames.dmp %_minimug.dmp: %.png
	PortraitFormatter $<
```

The idea is that you get the "list" of portrait data files to generate through dependency analysis with Event Assembler. (I may add support for listing dependencies in portrait-process itself in the future).

# Credits

Most tools were based off circleseverywhere's work.

| name               | original authors           | further additions    | notes |
| ------------------ | -------------------------- | -------------------- | ----- |
| `c2ea` & `n2c`     | circleseverywhere, zahlman | Crazycolorz5, StanH_ | - |
| `tmx2ea`           | circleseverywhere          | StanH_               | - |
| `text-process`     | circleseverywhere          | StanH_               | relies on `ParseFile` by CrazyColorz5 |
| `portrait-process` | StanH_                     | -                    | relies on `PortraitFormatter` by CrazyColorz5 |
