from setuptools import setup
import sys
sys.path.insert(0, '/Users/jiamingli_1/QuickNote')

# Execute the spec file
exec(open('QuickNoteMenuBar.spec').read())

setup(
    name='QuickNoteMenuBar',
    app=[exe],
    data_files=[],
    dist_dir='dist',
)
