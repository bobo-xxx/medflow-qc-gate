#!/bin/env python
import sys
import os
import json
import pandas as pd
from tools.tools import read, make_dir


in_rgs = json.loads(sys.argv[1])
out_rgs = json.loads(sys.argv[2])

print(in_rgs)
for i in range(len(in_rgs)):
    df = read(in_rgs[i]["value"])
    make_dir(out_rgs[i]["value"])
    df = df.map(lambda x: x.replace(" ", "") if isinstance(x, str) else x)
    df.to_csv(out_rgs[i]["value"], index=False)
