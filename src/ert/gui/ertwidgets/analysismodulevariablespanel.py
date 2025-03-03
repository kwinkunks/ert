from functools import partial

from annotated_types import Ge, Gt, Le
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QWidget,
)

from ert.config.analysis_module import AnalysisModule, IESSettings


class AnalysisModuleVariablesPanel(QWidget):
    def __init__(self, analysis_module: AnalysisModule, ensemble_size: int):
        QWidget.__init__(self)
        self.analysis_module = analysis_module

        layout = QFormLayout()
        layout.setVerticalSpacing(5)
        layout.setLabelAlignment(Qt.AlignLeft)
        layout.setHorizontalSpacing(150)

        self.blockSignals(True)

        layout.addRow(
            QLabel(
                "AnalysisModule: STD_ENKF"
                if type(analysis_module) != IESSettings
                else "AnalysisModule: IES_ENKF"
            )
        )
        layout.addRow(self.create_horizontal_line())

        if isinstance(analysis_module, IESSettings):
            for variable_name in (
                name for name in analysis_module.model_fields if "steplength" in name
            ):
                metadata = analysis_module.model_fields[variable_name]
                layout.addRow(
                    metadata.title,
                    self.createDoubleSpinBox(
                        variable_name,
                        analysis_module.__getattribute__(variable_name),
                        [val for val in metadata.metadata if isinstance(val, Ge)][0].ge,
                        [val for val in metadata.metadata if isinstance(val, Le)][0].le,
                        0.1,
                    ),
                )

            lab = QLabel(analysis_module.__doc__)
            lab.setStyleSheet("font-style: italic; font-size: 10pt; font-weight: 300")
            layout.addRow(lab)

            layout.addRow(self.create_horizontal_line())

        layout.addRow(QLabel("Inversion Algorithm"))
        bg = QButtonGroup(self)
        for button_id, s in enumerate(
            [
                "Exact inversion with diagonal R=I",
                "Subspace inversion with exact R",
                "Subspace inversion using R=EE'",
                "Subspace inversion using E",
            ],
            start=0,
        ):
            b = QRadioButton(s, self)
            b.setObjectName("IES_INVERSION_" + str(button_id))
            bg.addButton(b, button_id)
            layout.addRow(b)
        var_name = "enkf_truncation"
        metadata = analysis_module.model_fields[var_name]
        self.truncation_spinner = self.createDoubleSpinBox(
            var_name,
            analysis_module.enkf_truncation,
            [val for val in metadata.metadata if isinstance(val, Gt)][0].gt + 0.001,
            [val for val in metadata.metadata if isinstance(val, Le)][0].le,
            0.01,
        )
        self.truncation_spinner.setEnabled(False)
        layout.addRow("Singular value truncation", self.truncation_spinner)

        bg.idClicked.connect(self.update_inversion_algorithm)
        bg.buttons()[analysis_module.ies_inversion].click()  # update the current value

        if not isinstance(analysis_module, IESSettings):
            layout.addRow(self.create_horizontal_line())
            layout.addRow(QLabel("[EXPERIMENTAL]"))

            localization_frame = QFrame()
            localization_frame.setLayout(QHBoxLayout())
            localization_frame.layout().setContentsMargins(0, 0, 0, 0)

            metadata = analysis_module.model_fields[
                "localization_correlation_threshold"
            ]
            local_checkbox = QCheckBox(metadata.title)
            local_checkbox.setObjectName("localization")
            local_checkbox.clicked.connect(
                partial(
                    self.valueChanged,
                    "localization",
                    bool,
                    local_checkbox,
                )
            )
            var_name = "localization_correlation_threshold"
            metadata = analysis_module.model_fields[var_name]
            self.local_spinner = self.createDoubleSpinBox(
                var_name,
                analysis_module.correlation_threshold(ensemble_size),
                [val for val in metadata.metadata if isinstance(val, Ge)][0].ge,
                [val for val in metadata.metadata if isinstance(val, Le)][0].le,
                0.1,
            )
            self.local_spinner.setObjectName("localization_threshold")
            self.local_spinner.setEnabled(local_checkbox.isChecked())

            localization_frame.layout().addWidget(local_checkbox)
            localization_frame.layout().addWidget(self.local_spinner)
            layout.addRow(localization_frame)

            local_checkbox.stateChanged.connect(
                lambda localization_is_on: self.local_spinner.setEnabled(
                    localization_is_on
                )
            )
            local_checkbox.setChecked(analysis_module.localization)

        self.setLayout(layout)
        self.blockSignals(False)

    def update_inversion_algorithm(self, button_id):
        self.truncation_spinner.setEnabled(button_id != 0)  # not for exact inversion
        self.analysis_module.ies_inversion = button_id

    def create_horizontal_line(self) -> QFrame:
        hline = QFrame()
        hline.setFrameShape(QFrame.HLine)
        hline.setFrameShadow(QFrame.Sunken)
        hline.setFixedHeight(20)
        return hline

    def createDoubleSpinBox(
        self,
        variable_name,
        variable_value,
        min_value,
        max_value,
        step_length,
    ):
        spinner = QDoubleSpinBox()
        spinner.setDecimals(6)
        spinner.setFixedWidth(100)
        spinner.setObjectName(variable_name)

        spinner.setRange(
            min_value,
            max_value,
        )

        spinner.setSingleStep(step_length)
        spinner.setValue(variable_value)
        spinner.valueChanged.connect(
            partial(self.valueChanged, variable_name, float, spinner)
        )
        return spinner

    def valueChanged(self, variable_name, variable_type, variable_control):
        value = None
        if variable_type == bool:
            assert isinstance(variable_control, QCheckBox)
            value = variable_control.isChecked()
        elif variable_type == float:
            assert isinstance(variable_control, QDoubleSpinBox)
            value = variable_control.value()

        if value is not None:
            self.analysis_module.__setattr__(variable_name, value)
