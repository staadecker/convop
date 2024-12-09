from pathlib import Path
from typing import Any, Iterable, List, Optional, Union

import pandas as pd
import polars as pl
import pyoptinterface as poi

from pyoframe.constants import (
    CONST_TERM,
    Config,
    ObjSense,
    ObjSenseValue,
    PyoframeError,
    VType,
)
from pyoframe.core import Constraint, Variable
from pyoframe.model_element import ModelElement, ModelElementWithId
from pyoframe.objective import Objective
from pyoframe.util import Container, NamedVariableMapper, get_obj_repr


class Model:
    """
    Represents a mathematical optimization model. Add variables, constraints, and an objective to the model by setting attributes.

    Example:
        >>> m = pf.Model()
        >>> m.X = pf.Variable()
        >>> m.my_constraint = m.X <= 10
        >>> m
        <Model vars=1 constrs=1 objective=False>
    """

    _reserved_attributes = [
        "_variables",
        "_constraints",
        "_objective",
        "var_map",
        "io_mappers",
        "name",
        "solver",
        "poi",
        "params",
        "result",
        "attr",
        "sense",
        "objective",
        "_use_var_names",
        "ONE",
        "solver_name",
    ]

    def __init__(
        self,
        min_or_max: Union[ObjSense, ObjSenseValue] = "min",
        name=None,
        solver: Optional[str] = None,
        use_var_names=False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if solver is None:
            solver = Config.default_solver
        self.solver_name: str = solver
        self.poi: Optional["poi.gurobi.Model"] = Model.create_pyoptint_model(solver)
        self._variables: List[Variable] = []
        self._constraints: List[Constraint] = []
        self.sense = ObjSense(min_or_max)
        self._objective: Optional[Objective] = None
        self.var_map = (
            NamedVariableMapper(Variable) if Config.print_uses_variable_names else None
        )
        self.name = name

        self.params = Container(self._set_param, self._get_param)
        self.attr = Container(self._set_attr, self._get_attr)
        self._use_var_names = use_var_names

    @property
    def use_var_names(self):
        return self._use_var_names

    @staticmethod
    def create_pyoptint_model(solver: str):
        if solver == "gurobi":
            from pyoptinterface.gurobi import Model
        elif solver == "highs":
            from pyoptinterface.highs import Model
        # TODO add support for copt
        # elif solver == "copt":
        #     from pyoptinterface.copt import Model
        else:
            raise ValueError(
                f"Solver {solver} not recognized or supported."
            )  # pragma: no cover
        model = Model()
        constant_var = model.add_variable(lb=1, ub=1, name="ONE")
        if constant_var.index != CONST_TERM:
            raise ValueError(
                "The first variable should have index 0."
            )  # pragma: no cover
        return model

    @property
    def variables(self) -> List[Variable]:
        return self._variables

    @property
    def binary_variables(self) -> Iterable[Variable]:
        """
        Examples:
            >>> m = pf.Model()
            >>> m.X = pf.Variable(vtype=pf.VType.BINARY)
            >>> m.Y = pf.Variable()
            >>> len(list(m.binary_variables))
            1
        """
        return (v for v in self.variables if v.vtype == VType.INTEGER)

    @property
    def integer_variables(self) -> Iterable[Variable]:
        """
        Examples:
            >>> m = pf.Model()
            >>> m.X = pf.Variable(vtype=pf.VType.INTEGER)
            >>> m.Y = pf.Variable()
            >>> len(list(m.binary_variables))
            1
        """
        return (v for v in self.variables if v.vtype == VType.INTEGER)

    @property
    def constraints(self):
        return self._constraints

    @property
    def objective(self):
        return self._objective

    @objective.setter
    def objective(self, value):
        value = Objective(value)
        self._objective = value
        value.on_add_to_model(self, "objective")

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name not in Model._reserved_attributes and not isinstance(
            __value, (ModelElement, pl.DataFrame, pd.DataFrame)
        ):
            raise PyoframeError(
                f"Cannot set attribute '{__name}' on the model because it isn't of type ModelElement (e.g. Variable, Constraint, ...)"
            )

        if (
            isinstance(__value, ModelElement)
            and __name not in Model._reserved_attributes
        ):
            if isinstance(__value, ModelElementWithId):
                assert not hasattr(
                    self, __name
                ), f"Cannot create {__name} since it was already created."

            __value.on_add_to_model(self, __name)

            if isinstance(__value, Variable):
                self._variables.append(__value)
                if self.var_map is not None:
                    self.var_map.add(__value)
            elif isinstance(__value, Constraint):
                self._constraints.append(__value)
        return super().__setattr__(__name, __value)

    def __repr__(self) -> str:
        return get_obj_repr(
            self,
            name=self.name,
            vars=len(self.variables),
            constrs=len(self.constraints),
            objective=bool(self.objective),
        )

    def write(self, file_path: Union[Path, str]):
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        self.poi.write(str(file_path))

    def optimize(self):
        self.poi.optimize()

    def _set_param(self, name, value):
        self.poi.set_raw_parameter(name, value)

    def _get_param(self, name):
        return self.poi.get_raw_parameter(name)

    def _set_attr(self, name, value):
        try:
            self.poi.set_model_attribute(poi.ModelAttribute[name], value)
        except KeyError:
            self.poi.set_model_raw_attribute(name, value)

    def _get_attr(self, name):
        try:
            return self.poi.get_model_attribute(poi.ModelAttribute[name])
        except KeyError:
            return self.poi.get_model_raw_attribute(name)
