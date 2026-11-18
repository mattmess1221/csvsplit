# csvsplit

`csvsplit` is a script inspired by the unix command `split`. Its command interface tries to be as compatible with `split` possible.

You would want to use `csvsplit` when you have a very large `.csv` file which is too big (e.g. 100GB in size) to open in excel.

## Usage

Usage is `./csvsplit.py [OPTIONS] [FILE] [PREFIX]`

`FILE` can be omitted or set to `-` to use stdin.

`PREFIX` is set to `x` by default.

You can adjust the number of rows in each file using `-r/--records N`. The default value is `1000`.

For more info, run `./csvsplit.py --help`
