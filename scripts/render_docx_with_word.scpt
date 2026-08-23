on run argv
    set inputPath to item 1 of argv
    set outputPath to item 2 of argv
    tell application "Microsoft Word"
        set openedDocument to open POSIX file inputPath
        save as openedDocument file name outputPath file format format PDF
        close openedDocument saving no
    end tell
end run
