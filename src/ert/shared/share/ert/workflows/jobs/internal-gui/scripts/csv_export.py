import os
import re

import pandas
from qtpy.QtWidgets import QCheckBox

from ert import LibresFacade
from ert.config import CancelPluginException, ErtPlugin
from ert.gui.ertwidgets.customdialog import CustomDialog
from ert.gui.ertwidgets.listeditbox import ListEditBox
from ert.gui.ertwidgets.models.path_model import PathModel
from ert.gui.ertwidgets.pathchooser import PathChooser


def loadDesignMatrix(filename) -> pandas.DataFrame:
    dm = pandas.read_csv(filename, delim_whitespace=True)
    dm = dm.rename(columns={dm.columns[0]: "Realization"})
    dm = dm.set_index(["Realization"])
    return dm


class CSVExportJob(ErtPlugin):
    """
    Export of summary, misfit, design matrix data and gen kw into a single CSV file.

    The script expects a single argument:

    output_file: this is the path to the file to output the CSV data to

    Optional arguments:

    case_list: a comma separated list of cases to export (no spaces allowed)
               if no list is provided the current case is exported
               a single * can be used to export all cases

    design_matrix: a path to a file containing the design matrix

    infer_iteration: If True the script will try to infer the iteration number
                     by looking at the suffix of the case name (i.e. default_2
                     = iteration 2). If False the script will use the ordering
                     of the case list: the first item will be iteration 0,
                     the second item will be iteration 1...

    The script also looks for default values for output path and design matrix
    path to present in the GUI. These can be specified with DATA_KW keyword in
    the config file:
        DATA_KW <CSV_OUTPUT_PATH> {some path}
        DATA_KW <DESIGN_MATRIX_PATH> {some path}
    """

    INFER_HELP = (
        "<html>"
        "If this is checked the iteration number will be inferred from the name i.e.:"
        "<ul>"
        "<li>case_name -> iteration: 0</li>"
        "<li>case_name_0 -> iteration: 0</li>"
        "<li>case_name_2 -> iteration: 2</li>"
        "<li>case_0, case_2, case_5 -> iterations: 0, 2, 5</li>"
        "</ul>"
        "Leave this unchecked to set iteration number to the order of the listed cases:"
        "<ul><li>case_0, case_2, case_5 -> iterations: 0, 1, 2</li></ul>"
        "<br/>"
        "</html>"
    )

    def getName(self):
        return "CSV Export"

    def getDescription(self):
        return (
            "Export GenKW, design matrix, misfit data "
            "and summary data into a single CSV file."
        )

    def inferIterationNumber(self, case_name):
        pattern = re.compile("_([0-9]+$)")
        match = pattern.search(case_name)

        if match is not None:
            return int(match.group(1))
        return 0

    def run(
        self,
        output_file,
        case_list=None,
        design_matrix_path=None,
        infer_iteration=True,
        drop_const_cols=False,
    ):
        cases = []
        facade = LibresFacade(self.ert())

        if case_list is not None:
            if case_list.strip() == "*":
                cases = self.getAllCaseList()
            else:
                cases = case_list.split(",")

        if case_list is None or len(cases) == 0:
            cases = "default"

        if design_matrix_path is not None:
            if not os.path.exists(design_matrix_path):
                raise UserWarning("The design matrix file does not exists!")

            if not os.path.isfile(design_matrix_path):
                raise UserWarning("The design matrix is not a file!")

        data = pandas.DataFrame()

        for case in cases:
            case = case.strip()

            try:
                ensemble = self.storage.get_ensemble_by_name(case)
            except KeyError as exc:
                raise UserWarning(f"The case '{case}' does not exist!") from exc

            if not ensemble.has_data:
                raise UserWarning(f"The case '{case}' does not have any data!")

            case_data = ensemble.load_all_gen_kw_data()

            if design_matrix_path is not None:
                design_matrix_data = loadDesignMatrix(design_matrix_path)
                if not design_matrix_data.empty:
                    case_data = case_data.join(design_matrix_data, how="outer")

            misfit_data = facade.load_all_misfit_data(ensemble)
            if not misfit_data.empty:
                case_data = case_data.join(misfit_data, how="outer")

            summary_data = ensemble.load_all_summary_data()
            if not summary_data.empty:
                case_data = case_data.join(summary_data, how="outer")
            else:
                case_data["Date"] = None
                case_data.set_index(["Date"], append=True, inplace=True)

            case_data["Iteration"] = ensemble.iteration
            case_data["Case"] = case
            case_data.set_index(["Case", "Iteration"], append=True, inplace=True)

            data = pandas.concat([data, case_data])

        data = data.reorder_levels(["Realization", "Iteration", "Date", "Case"])
        if drop_const_cols:
            data = data.loc[:, (data != data.iloc[0]).any()]

        data.to_csv(output_file)

        export_info = (
            f"Exported {len(data.index)} rows and {len(data.columns)} "
            f"columns to {output_file}."
        )
        return export_info

    def getArguments(self, parent=None):
        description = "The CSV export requires some information before it starts:"
        dialog = CustomDialog("CSV Export", description, parent)

        default_csv_output_path = self.get_context_value(
            "<CSV_OUTPUT_PATH>", default="output.csv"
        )
        output_path_model = PathModel(default_csv_output_path)
        output_path_chooser = PathChooser(output_path_model)

        design_matrix_default = self.get_context_value(
            "<DESIGN_MATRIX_PATH>", default=""
        )
        design_matrix_path_model = PathModel(
            design_matrix_default, is_required=False, must_exist=True
        )
        design_matrix_path_chooser = PathChooser(design_matrix_path_model)

        list_edit = ListEditBox(self.getAllCaseList())

        infer_iteration_check = QCheckBox()
        infer_iteration_check.setChecked(True)
        infer_iteration_check.setToolTip(CSVExportJob.INFER_HELP)

        drop_const_columns_check = QCheckBox()
        drop_const_columns_check.setChecked(False)
        drop_const_columns_check.setToolTip(
            "If checked, exclude columns whose value is the same for every entry"
        )

        dialog.addLabeledOption("Output file path", output_path_chooser)
        dialog.addLabeledOption("Design matrix path", design_matrix_path_chooser)
        dialog.addLabeledOption("List of cases to export", list_edit)
        dialog.addLabeledOption("Infer iteration number", infer_iteration_check)
        dialog.addLabeledOption("Drop constant columns", drop_const_columns_check)

        dialog.addButtons()

        success = dialog.showAndTell()

        if success:
            design_matrix_path = design_matrix_path_model.getPath()
            if design_matrix_path.strip() == "":
                design_matrix_path = None

            case_list = ",".join(list_edit.getItems())

            return [
                output_path_model.getPath(),
                case_list,
                design_matrix_path,
                infer_iteration_check.isChecked(),
                drop_const_columns_check.isChecked(),
            ]

        raise CancelPluginException("User cancelled!")

    def get_context_value(self, name, default):
        context = self.ert().ert_config.substitution_list
        if name in context:
            return context[name]
        return default

    def getAllCaseList(self):
        all_case_list = [case.name for case in self.storage.ensembles if case.has_data]
        return all_case_list
