import pandas as pd
from typing import Dict, List
from collections.abc import Iterable


def make_csv(listOfObjects:List[Dict]) -> str:
    if listOfObjects is None or len(listOfObjects) < 1:
        return "status,message\nerror,No data to convert to CSV"
    elif not isinstance(listOfObjects, Iterable):
        return "status,message\nerror,Got non iteratable object for conversion to CSV"

    dataframe = pd.DataFrame(listOfObjects)
    output = dataframe.to_csv(index=False)

    return output
