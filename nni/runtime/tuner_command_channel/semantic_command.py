# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from dataclasses import dataclass
import dataclasses
import json
import re
from typing import Any, List, Literal
import typeguard
from nni.runtime.tuner_command_channel.command_type import CommandType

new_to_old ={'Initialize': CommandType.Initialize,
'RequestTrialJobs': CommandType.RequestTrialJobs,
'ReportMetricData': CommandType.ReportMetricData,
'UpdateSearchSpace': CommandType.UpdateSearchSpace,
'ImportData': CommandType.ImportData,
'AddCustomizedTrialJob': CommandType.AddCustomizedTrialJob,
'TrialEnd': CommandType.TrialEnd,
'Terminate': CommandType.Terminate,
'Ping': CommandType.Ping,
'Initialized': CommandType.Initialized,
'NewTrialJob': CommandType.NewTrialJob,
'SendTrialJobParameter': CommandType.SendTrialJobParameter,
'NoMoreTrialJobs': CommandType.NoMoreTrialJobs,
'KillTrialJob': CommandType.KillTrialJob
}

@dataclass
class BaseCommand:
    command_type: str

    def dump(self) -> str:
        command_dict = {key:val for key, val in self.__dict__.items() if key != 'command_type'}
        return json.dumps(command_dict)

    def validate(self):
        validate_type(self)

    def _to_legacy_command_type(self) -> tuple[CommandType, str]:
        if self.command_type not in new_to_old:
            raise AssertionError('Unsupported command type: {}'.format(self.command_type))
        old_command_type = new_to_old[self.command_type]

        command_dict = {key:val for key, val in self.__dict__.items() if key != 'command_type'}
        command_json = json.dumps(command_dict)
        return old_command_type, command_json

    @classmethod
    def load(cls, command_type, command_json: str):
        command_dict = {}
        if len(command_json) == 0:
            command_dict['command_type'] = command_type
            return cls(**command_dict)
        command_dict = json.loads(command_json)
        command_dict['command_type'] = command_type
        return cls(**command_dict)

@dataclass
class Initialize(BaseCommand):
    search_space: dict

    def _to_legacy_command_type(self) -> tuple[CommandType, str]:
        old_command_type = new_to_old[self.command_type]
        command_json = json.dumps(self.search_space)
        return old_command_type, command_json

    @classmethod
    def load(cls, command_type, command_json: str):
        command_dict = {}
        command_dict['search_space'] = json.loads(command_json)
        command_dict['command_type'] = command_type
        return cls(**command_dict)

@dataclass
class RequestTrialJobs(BaseCommand):
    job_num: int

    def _to_legacy_command_type(self) -> tuple[CommandType, str]:
        old_command_type = new_to_old[self.command_type]
        command_json = repr(self.job_num)
        return old_command_type, command_json

    @classmethod
    def load(cls, command_type, command_json: str):
        command_dict = {}
        command_dict['job_num'] = json.loads(command_json)
        command_dict['command_type'] = command_type
        return cls(**command_dict)

@dataclass
class ReportMetricData(BaseCommand):
    trial_job_id: str
    parameter_id: int
    parameter_index: int
    parameters: Any
    type: Literal['FINAL', 'PERIODICAL', 'REQUEST_PARAMETER']
    value: str
    sequence: int

@dataclass
class UpdateSearchSpace(BaseCommand):
    search_space: dict

@dataclass
class ImportData(BaseCommand):
    command_type: str
    data: List[dict]

@dataclass
class AddCustomizedTrialJob(BaseCommand):
    def _to_legacy_command_type(self) -> tuple[CommandType, str]:
        old_command_type = new_to_old[self.command_type]
        return old_command_type, ''

@dataclass
class TrialEnd(BaseCommand):
    trial_job_id: str
    event: str
    hyper_params: dict

    @classmethod
    def load(cls, command_type, command_json: str):
        hyper_params_json = command_json.split("hyper_params\":")[1][1:-2]
        command_dict = {}
        command_dict['hyper_params'] = json.loads(eval('\''+hyper_params_json+'\''))
        subcommand = re.findall(r':"(.*?)"', command_json.split("hyper_params\":")[0])
        command_dict['trial_job_id'] = subcommand[0]
        command_dict['event'] = subcommand[1]
        command_dict['command_type'] = command_type
        return cls(**command_dict)

@dataclass
class Terminate(BaseCommand):
    def _to_legacy_command_type(self) -> tuple[CommandType, str]:
        old_command_type = new_to_old[self.command_type]
        return old_command_type, ''

@dataclass
class Ping(BaseCommand):
    def _to_legacy_command_type(self) -> tuple[CommandType, str]:
        old_command_type = new_to_old[self.command_type]
        return old_command_type, ''

@dataclass
class Initialized(BaseCommand):
    def _to_legacy_command_type(self) -> tuple[CommandType, str]:
        old_command_type = new_to_old[self.command_type]
        return old_command_type, ''

@dataclass
class NewTrialJob(BaseCommand):
    parameter_id: int
    parameter_source: str
    parameters: Any
    parameter_index: int

@dataclass
class SendTrialJobParameter(BaseCommand):
    trial_job_id: str
    parameter_id: int
    parameter_index: int
    parameters: Any
    parameter_source: str

@dataclass
class NoMoreTrialJobs(BaseCommand):
    parameter_id: int
    parameter_source: str
    parameters: Any
    parameter_index: int

@dataclass
class KillTrialJob(BaseCommand):
    trial_job_id: str

def validate_type(command):
    class_name = type(command).__name__
    for field in dataclasses.fields(command):
        value = getattr(command, field.name)
        #check existense
        if is_missing(value):
            raise ValueError(f'{class_name}: {field.name} is not set')
        if not is_instance(value, field.type):
            raise ValueError(f'{class_name}: type of {field.name} ({repr(value)}) is not {field.type}')

def is_missing(value):
    """
    Used to check whether a dataclass field has ever been assigned.

    If a field without default value has never been assigned, it will have a special value ``MISSING``.
    This function checks if the parameter is ``MISSING``.
    """
    # MISSING is not singleton and there is no official API to check it
    return isinstance(value, type(dataclasses.MISSING))

def is_instance(value, type_hint):
    try:
        typeguard.check_type('_', value, type_hint)
    except TypeError:
        return False
    return True