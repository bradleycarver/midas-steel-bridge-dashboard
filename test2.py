# here im testing if you can rename existing nodes or no
# ok answer is no.


# SETUP
from midas_civil import *
import pandas as pd

MAPI_KEY('eyJ1ciI6ImJjYXJ2ZTAxQHN0dWRlbnQudWJjLmNhIiwicGciOiJjaXZpbCIsImNuIjoicmZ3Q2RKZk9SUSJ9.6c5345beaa7eddb236c29c53639bbc6bdfa9e7323618b3b7ffda74fc260bf1f3')
MAPI_BASEURL('https://moa-engineers.midasit.com:443/civil')

Model.units('LBF','IN')

Node(0, 26, 0, 69).create()


