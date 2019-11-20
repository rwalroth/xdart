from watchgod import watch

path_to_watch = "P:\\bl2-1"

for changes in watch(path_to_watch):
    print(changes)