import os
import shutil

def main():
    if not os.path.exists('config.yaml'):
        shutil.copy('config_sample.yaml', 'config.yaml')

if __name__ == '__main__':
    main()