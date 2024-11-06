import subprocess


class DBTSubprocess:
    def call(self, command, shell=False):
        subprocess.call(command, shell=shell)
