#!/bin/env python
import sys
import logging
import yaml
import json
import pandas as pd
from pathlib import Path
from tools.tools import read, make_dir


def pd2dict(info_df: pd.DataFrame) -> dict:
    """
    Convert pandas dataframe to dict format,
    this function main fill all NaN with '' and convert index to string.

    Args:
        info_df (pd.DataFrame) 

    Returns:
        dict
    """
    info_df = info_df.fillna('')
    info_df.index = info_df.index.astype('str')
    return info_df.to_dict()


def filter_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter dataframe, drop rows and columns with all NaN,
    remove space from column names and cells.

    Args:
        df (pd.DataFrame): 

    Returns:
        pd.DataFrame: 
    """
    df = df.dropna(how='all')
    df = df.map(lambda x: str(x).replace(' ', ''))
    df.columns = [str(x).replace(' ', '') for x in df.columns]
    return df


def parse_confirm(file: Path | str, logger: logging.Logger = logging.getLogger()) -> dict:
    """
    Get confirm information from excel file.

    Args:
        file (Path | str): excel file path.
        logger (logging.Logger): logger.

    Raises:
        ValueError: _description_
        ValueError: _description_

    Returns:
        dict: confirm information.
    """
    cfg = {}
    if str(file).endswith(".yaml"):
        with open(file, "r") as f:
            cfg = yaml.load(f, Loader=yaml.FullLoader)
    else:
        df = read(file)
        df.columns = [str(x).replace(' ', '').lower() for x in df.columns]
        dic = df.to_dict()
        if "key" in dic and "value" in dic:
            cfg = {k: v for k, v in zip(
                dic['key'].values(), dic['value'].values())}
    return cfg


def check_map(in_map: Path | str | None, out_map: Path | str | None, data_set_name: str,
              confirm: dict, control_name: str | None, color1: str = "#1f77b4", color2: str = "#d62728",
              logger: logging.Logger = logging.getLogger()) -> tuple[dict, pd.DataFrame | None]:
    """_summary_

    Args:
        in_mat (Path | str): _description_
        in_map (Path | str): _description_
        out_mat (Path | str): _description_
        out_map (Path | str): _description_
        confirm (dict): _description_
        logger (logging.Logger, optional): _description_. Defaults to logging.getLogger().

    Raises:
        ValueError: _description_
    """
    if in_map is not None:
        make_dir(out_map)
        group = read(in_map)
        
        for column in group.columns:
            group[column] = pd.Series([str(v).replace("-", ".") for v in group[column]])
        mapping = group.groupby("sample_group", sort=False)[
            group.columns[0]].agg(list).to_dict()
        mapping = {str(key): value for key, value in mapping.items()}
        g = mapping.keys()
        if len(g) == 1:
            treat_name = list(g)[0]
            control_name = ""
        elif control_name and control_name in g:
            treat_name = set(g).difference([control_name]).pop()
            print(f"确认实验组 {treat_name}，对照组 {control_name} ")
        else:
            logger.warning(
                f"请注意对照组 {control_name} 未在分组表分组 {",".join(list(g))} 中找到！")
            control_name, treat_name = list(g)[0:2]
            logger.warning("分析信息中组名不匹配，自动使用分组表中第一个分组作为对照组，第二个分组作为实验组！")
            
        c_num = len(mapping.get(control_name, []))
        t_num = len(mapping.get(treat_name, []))
        group2 = pd.DataFrame({
            "ID": mapping.get(control_name, []) + mapping.get(treat_name, []),
            "group": [control_name] * c_num + [treat_name] * t_num,
            "color": [color1] * c_num + [color2] * t_num
            })
        group2.to_csv(out_map, index=False)
    else:
        group2 = None
        control_name = None
        treat_name = None
        c_num = 0
        t_num = 0
    confirm["control"] = control_name
    confirm["treat"] = treat_name
    confirm["control_raw"] = confirm["control"]
    confirm["treat_raw"] = confirm["treat"]
    confirm["control_cn_raw"] = confirm["control_cn"]
    confirm["treat_cn_raw"] = confirm["treat_cn"]
    confirm["control_num"] = str(c_num)
    confirm["treat_num"] = str(t_num)
    confirm["total_num"] = str(c_num + t_num)
    if "data_set_name" not in confirm:
        confirm["data_set_name"] = "{<color=blue>整合的GEO数据集（Combined Datasets）}"
    if str(data_set_name) != "None":
        confirm["data_set_name"] = data_set_name
    confirm["data_set_name_raw"] = confirm["data_set_name"]
    return confirm, group2

def check_mat(in_mat: Path | str, map: pd.DataFrame | None, out_mat: Path | str):
    make_dir(out_mat)
    data = read(in_mat, index_col=0)
    data.columns = [str(v).replace("-", ".") for v in data.columns]
    # data.index = pd.Index([str(v).replace("-", ".") for v in data.index])
    if map is not None:
        data = data.loc[:, map.iloc[:, 0]]
    data.to_csv(out_mat)

def check_clinical(in_clinical: Path | str, out_clinical: Path | str):
    make_dir(out_clinical)
    data = read(in_clinical)
    data["Sample_id"] = [str(v).replace("-", ".") for v in data["Sample_id"]]
    data.to_csv(out_clinical, index=False)

if __name__ == "__main__":
    confirm = parse_confirm(sys.argv[1])
    tcga_dic = json.loads(sys.argv[2])
    out_dic = json.loads(sys.argv[3])
    out_dir = sys.argv[4]
    out_confirm=sys.argv[5]
    out_dic = {k: Path(out_dir, v) for k, v in out_dic.items() if v is not None}
    
    confirm, map = check_map(
        in_map=tcga_dic.get("group", None), out_map=out_dic.get("group", None),
        confirm=confirm, color1=sys.argv[6], color2=sys.argv[7], control_name=sys.argv[8], data_set_name=sys.argv[9]
    )
    for key in tcga_dic:
        if key == "group": continue
        if key == "clinical": 
            check_clinical(tcga_dic[key], out_dic[key])
        else:
            check_mat(tcga_dic[key], map, out_dic[key])
    make_dir(out_confirm)
    with open(out_confirm, 'w') as f:
        yaml.dump(confirm, f, default_flow_style=False, allow_unicode=True)