import subprocess


class DBTSubprocess:
    def call(command, shell=False):
        subprocess.call(command, shell=shell)
