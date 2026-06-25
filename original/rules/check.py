import os
import requests
import json
from pathlib import Path
from .rule import MyRule, RuleSet, flag, Parameter
from .report import Report



class Check_confirm(MyRule):
    def __init__(self, in_confirm, in_mat, in_map, control_color, treat_color, out_mat, out_map, confirm, control_name, data_set_name, config=None):
        self.script = "check_confirm.py"
        self.args = ["{params.in_confirm}", "{input.in_mat}", "{input.in_map}",
                     "{output.out_mat}", "{output.out_map}", "{params.confirm}", control_color, treat_color, control_name, data_set_name]
        self.out_mat = self.out_prefix_call(out_mat)
        self.out_map = self.out_prefix_call(out_map)

class GeoData(MyRule):
    def __init__(self, **kwargs):
        self.script = "GEO_Datasets.R"
        self._params = {"out_dir": self.out_prefix_call(kwargs["out_dir"])}
        self.args = ["{params.gse}", "{params.disease_name}", "{params.db_dir}", "{params.in_confirm}", "{params.out_confirm}",
                      "{params.out_dir}", "{output.out_mat}", "{output.out_map}", "{params.color_panel}",
                      "{params.control_color}", "{params.treat_color}", "{params.control_name}"]

class TumorData(MyRule):
    def __init__(self, in_confirm, tcga_dic, out_dic, confirm, control_color, treat_color, control_name, data_set_name):
        self._input = {f"in_{k}": v for k, v in tcga_dic.items() if v}
        self._output = {f"out_{k}": v for k, v in out_dic.items() if tcga_dic[k]}
        self._params = {"out_dir": self.out_prefix_call("."),
                        "tcga_dic": json.dumps(tcga_dic, default=str), "out_dic": json.dumps(out_dic, default=str)}
        self.script = "check_tcga.py"
        self.args = ["{params.in_confirm}", "{params.tcga_dic}", "{params.out_dic}", "{params.out_dir}", "{params.confirm}",
                     control_color, treat_color, control_name, data_set_name]
        self.out_map = self.out_prefix_call(out_dic["group"]) if tcga_dic["group"] else None
        self.counts = self.out_prefix_call(out_dic["counts"]) if tcga_dic["counts"] else None
        self.fpkm = self.out_prefix_call(out_dic["fpkm"]) if tcga_dic["fpkm"] else None
        self.tpm = self.out_prefix_call(out_dic["tpm"]) if tcga_dic["tpm"] else None
        self.clinical = self.out_prefix_call(out_dic["clinical"]) if tcga_dic["clinical"] else None

def check_tcga(api, db_dir, cfg):
    tcga = cfg["tcga"]
    tcga_files: dict[str, Path | None] = {
        "group": Path(db_dir, "TCGA-Group", f"TCGA-{tcga}_group.csv"),
        "counts": Path(db_dir, "TCGA-Counts", f"TCGA-{tcga}_Counts.csv"),
        "fpkm": Path(db_dir, "TCGA-FPKM_log", f"TCGA-{tcga}_FPKM.csv"),
        "tpm": Path(db_dir, "TCGA-TPM_log", f"TCGA-{tcga}_TPM.csv"),
        "clinical": Path(db_dir, "TCGA-Clinical", f"TCGA-{tcga}_clinical.csv")
    }
    for name, path in tcga_files.items():
        if cfg.get(name, False):
            print(f"优先使用手动输入的文件：{cfg[name]}")
            tcga_files[name] = cfg[name]
        else:
            if not path or not path.exists():
                print(f"{name}: {path} 不存在")
                tcga_files[name] = None
    if all([path is None for path in tcga_files.values()]):
        raise FileNotFoundError("没有找到TCGA数据文件，请检查配置文件或输入")
    return tcga_files, tcga
    
def check_geo(disease_name, gse: list, api, db_dir):
    info = []
    gse_available = []
    colnames = ["gse", "gse_exists", "available", "tpm_exists", "mat_exists", "log_exists", "map_exists", "pd_exists"]
    msg_list = []
    tpm_datasets = []  # 记录包含TPM数据的数据集
    for i in gse:
        gse_path = Path(db_dir, disease_name, i)
        tpm_path = gse_path / "{}_TPM.csv".format(i)
        mat_path = gse_path / "{}_expression_matrix.csv".format(i)
        log_path = gse_path / "{}_expression_matrix_log.csv".format(i)
        map_path = gse_path / "{}_group_info.csv".format(i)
        pd_path = gse_path / "{}PD.csv".format(i)
        mat_available = tpm_path.exists() or mat_path.exists() or log_path.exists()
        map_available = map_path.exists()
        pd_available = pd_path.exists()
        # 检查是否为TPM数据（高通量数据）
        if tpm_path.exists():
            tpm_datasets.append(i)
        msg = ""
        if not mat_available:
            msg += "Expression matrix not available for {}. ".format(i)
        if not map_available:
            msg += "\nGroup info not available for {}. ".format(i)
        if not pd_available:
            msg += "\nPD info not available for {}. ".format(i)
        if msg:
            msg_list.append("\033[31m" + msg + "\033[0m")
        available = mat_available and map_available and pd_available
        gse_available.append(available)
        info.append({
            "gse": i, "disease_name": disease_name, "gse_exists": gse_path.exists() , "available": available,
            "tpm_exists": tpm_path.exists(), "mat_exists": mat_path.exists(), "log_exists": log_path.exists(), "map_exists": map_path.exists(), "pd_exists": pd_path.exists()
        })
    # 如果配置了多个GSE且其中包含TPM数据，则报错提示
    if len(gse) > 1 and tpm_datasets:
        raise ValueError(
            "检测到以下数据集包含高通量数据（TPM格式）：{}。\n"
            "这些数据集不建议与其他数据集合并分析，因为高通量数据与芯片数据存在系统性差异，\n"
            "强行合并会导致批次效应无法有效校正。建议单独分析这些数据集。".format(", ".join(tpm_datasets))
        )
    if not all(gse_available):
        try:
            requests.post(
                url=os.path.join(api, "gse/uploadinfo"),
                json={
                    "user": os.getenv("USER"), "info": info, "db_dir": str(db_dir), "colnames": colnames
                }
            )
        except Exception as e:
            print("上传geo数据失败！")
    return all(gse_available), "\n".join(msg_list)
    
class CheckTcga(RuleSet):
    def __init__(self, config, name, in_confirm, api):
        super().__init__(config)
        config = self.config
        self.key = "tcga_input"
        self.cfg = config[name]
        self.pre_config = config[name]
        self.geo = False
        self.ai_file = {
        }
        
        tcga_dic, tcga = check_tcga(api, Path(config["global"]["tcga_dir"]), config[name])

        out_dic = {
            "group": Path("output", f"TCGA-{tcga}_group.csv"),
            "counts": Path("output", f"TCGA-{tcga}_Counts.csv"),
            "fpkm": Path("output", f"TCGA-{tcga}_FPKM.csv"),
            "tpm": Path("output", f"TCGA-{tcga}_TPM.csv"),
            "clinical": Path("output", f"TCGA-{tcga}_clinical.csv")
        }
        data_set_name_raw = config[name]["data_set_name"] if config[name].get("data_set_name") else f"{{<color=blue>{config[name]["tcga"]}数据集（{config[name]["tcga"]}）}}"
        data_set_name = data_set_name_raw.replace("{", "{{").replace("}", "}}")
        check_confirm = TumorData(
            in_confirm=in_confirm,
            tcga_dic=tcga_dic,
            out_dic=out_dic,
            control_color=config[name]["control_color"],
            treat_color=config[name]["treat_color"],
            control_name=config[name].get("control_name"),
            confirm=self.confirm_file,
            data_set_name=data_set_name,
        )
        self.append(check_confirm)
        self.out_confirm = self.confirm_file
        self._export["out_map"] = Parameter(check_confirm.out_map, value_type="path", name="map")
        default_mat = config[name].get("default_mat", "fpkm")
        if default_mat == "tpm":
            self._export["out_mat"] = Parameter(check_confirm.tpm, value_type="path", name="mat")
        else:
            self._export["out_mat"] = Parameter(check_confirm.fpkm, value_type="path", name="mat")
        self._export["out_clinical"] = Parameter(check_confirm.clinical, value_type="path", name="clinical")
        self._export["counts"] = Parameter(check_confirm.counts, value_type="path", name="counts")
        self._export["fpkm"] = Parameter(check_confirm.fpkm, value_type="path", name="fpkm")
        self._export["tpm"] = Parameter(check_confirm.tpm, value_type="path", name="tpm")
        self._export["clinical"] = Parameter(check_confirm.clinical, value_type="path", name="clinical")

    def get_input(self, key) -> str | None:
        dic = self.get_inputs(key)
        if dic:
            return list(dic.values())[0]
        else:
            return None

    def get_inputs(self, key) -> dict | None:
        res = {}
        files = []
        if key not in self.cfg:
            return res
        input = self.cfg[key]
        if input is None:
            files = []
        elif isinstance(input, str):
            files = [str(s).strip() for s in input.split(",")]
        elif isinstance(input, list):
            files = input

        for i, v in enumerate(files):
            file = Path(v)
            if os.path.exists(file):
                res.update({
                    key + str(i): file.absolute()
                })
            else:
                raise FileNotFoundError(f"{file} 文件不存在, 没有请留空。")
        return res

class Check(RuleSet):
    def __init__(self, config, name, in_confirm, api):
        super().__init__(config)
        config = self.config
        self.key = "input"
        self.cfg = config[name]
        self.geo = False
        self.in_rgs = self.get_inputs("rgs")
        self.ai_file = {
            "a":  Path("assets", "ai", "Z-BatchEffects.ai")
        }
        if config[name]["disease_name"] and config[name]["gse"]: 
            gse_available, msg = check_geo(config[name]["disease_name"], config[name]["gse"], api=api, db_dir=Path(config["global"]["db_dir"]))
        else:
            raise ValueError(f"请填写 {name} 的 disease_name 和 gse 字段！")
        if not config[name].get("control_name", None):
            raise ValueError(f"请填写 {name} 的 control_name字段！")
        
        if config[name].get("group", False) and config[name].get("data", False):
            if gse_available:
                print(f"优先使用手动输入的文件：{config[name]["group"]} and {config[name]["data"]}")
            self.in_mat = self.get_input("data")
            self.in_map = self.get_input("group")
        elif gse_available:
            self.geo = True
            if len(config[name]["gse"]) > 1:
                out_mat=Path("output", "Combined_Datasets_Matrix.csv")
                out_map=Path("output", "Combined_Datasets_Group.csv")
            else:
                out_mat=Path("output", config[name]["gse"][0] + "_Matrix.csv")
                out_map=Path("output", config[name]["gse"][0] + "_Group.csv")
            geo = GeoData(
                gse=",".join(config[name]["gse"]),
                disease_name=config[name]["disease_name"],
                db_dir=Path(config["global"]["db_dir"]),
                in_confirm=in_confirm,
                out_confirm=self.confirm_file,
                out_dir="output",
                out_mat=out_mat,
                out_map=out_map,
                color_panel=",".join(config["global"]["color_panel"]),
                control_color=config[name]["control_color"],
                treat_color=config[name]["treat_color"],
                control_name=config[name].get("control_name")
            )
            self.append(geo)
            self.in_mat = geo._export["out_mat"]
            self.in_map = geo._export["out_map"]
            in_confirm = self.confirm_file
        else:
            raise ValueError(msg)

        check_confirm = Check_confirm(
            in_confirm=in_confirm,
            in_mat=self.in_mat,
            in_map=self.in_map,
            control_color=config[name]["control_color"],
            treat_color=config[name]["treat_color"],
            control_name=config[name].get("control_name"),
            out_mat="mat.csv", out_map="map.csv",
            confirm=self.confirm_file,
            data_set_name=config[name]["data_set_name"]
        )
        self.append(check_confirm)
        self.out_confirm = self.confirm_file
        data_type = config[name].get("data_type", "")
        self._export["out_mat"] = Parameter(check_confirm.out_mat, value_type="path", name="mat", mark=data_type if data_type else "mat")
        self._export["out_map"] = Parameter(check_confirm.out_map, value_type="path", name="map")

    def get_input(self, key) -> str | None:
        dic = self.get_inputs(key)
        if dic:
            return list(dic.values())[0]
        else:
            return None

    def get_inputs(self, key) -> str | dict | None:
        res = {}
        files = []
        if key not in self.cfg:
            return res
        input = self.cfg[key]
        if input is None:
            files = []
        elif isinstance(input, str):
            files = [str(s).strip() for s in input.split(",")]
        elif isinstance(input, list):
            files = input

        for i, v in enumerate(files):
            file = Path(v)
            if os.path.exists(file):
                res.update({
                    key + str(i): file.absolute()
                })
            else:
                raise FileNotFoundError(f"{file} 文件不存在, 没有请留空。")
        return res
    
    @classmethod
    def parse_input(self, input, key=""):
        res = {}
        if input is dict:
            for k, file in input.items():
                if os.path.exists(file):
                    res.update({
                        k:  Path(file).absolute()
                    })
                else:
                    raise FileNotFoundError(f"{file} 文件不存在, 没有请留空。")
        else:
            if input is str:
                files = input.split(",")
            else:
                files = input
            for i, v in enumerate(files):
                file = Path(v)
                if os.path.exists(file):
                    res.update({
                        key + str(i): file.absolute()
                    })
                else:
                    raise FileNotFoundError(f"{file} 文件不存在, 没有请留空。")        