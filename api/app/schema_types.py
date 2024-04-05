from datetime import datetime
from typing import Any, Optional, Union

import pytz
from pydantic import BaseModel, validator


class Bestand(BaseModel):
    bytesField: Union[str, None]
    mimeTypeField: Union[str, None]
    naamField: Union[str, None]


class MorMeldingAanmakenRequest(BaseModel):
    aanvullendeInformatieField: Union[str, None] = None
    aanvullendeVragenField: Union[list[Union[dict[str, list[str]], None]], None] = None
    bijlagenField: Union[list[Bestand], None] = None
    fotosField: Union[list[str], None]
    huisnummerField: Union[str, None] = None
    kanaalField: Union[str, None]
    onderwerpField: Union[str, None]
    lichtpuntenField: Union[list[int], None]
    loginnaamField: Union[str, None] = None
    melderEmailField: Union[str, None] = None
    melderNaamField: Union[str, None] = None
    melderTelefoonField: Union[str, None] = None
    meldingsnummerField: Union[str, None]
    naderePlaatsbepalingField: Union[str, None]
    omschrijvingField: Union[str, None] = None
    straatnaamField: Union[str, None]
    spoedField: bool
    xCoordField: float
    yCoordField: float
    aanmaakDatumField: Union[datetime, None]
    adoptantnummerField: Union[int, None] = None

    @validator("aanmaakDatumField", pre=False)
    def parse_aanmaakDatumField(cls, value):
        return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # @validator("aanvullendeVragenField")
    # def validate_aanvullendeVragenField(cls, v):
    #     if not v:
    #         return v
    #     try:
    #         if not isinstance(v, list):
    #             raise ValueError(
    #                 f"Invalid format for aanvullendeVragenField: not a list: {v}"
    #             )
    #         for qa in v:
    #             if (
    #                 not isinstance(qa, dict)
    #                 or "question" not in qa
    #                 or "answers" not in qa
    #                 or not isinstance(qa["answers"], list)
    #             ):
    #                 raise ValueError(
    #                     f"Invalid format for aanvullendeVragenField: incorrect structure: {v}"
    #                 )
    #     except Exception as e:
    #         raise ValueError(
    #             f"An error occured validating aanvullendeVragenField: {str(e)}. {v}"
    #         )
    #     return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        now = datetime.now(pytz.timezone("Europe/Amsterdam")).isoformat()
        schema_extra = {
            "example": {
                "aanvullendeInformatieField": "string",
                "aanvullendeVragenField": [
                    {"question": "string", "answers": ["string"]}
                ],
                "bijlagenField": [
                    {
                        "bytesField": "base64_string",
                        "mimeTypeField": "string",
                        "naamField": "string",
                    }
                ],
                "fotosField": ["base64_string"],
                "huisnummerField": "string",
                "kanaalField": "string",
                "onderwerpField": "string",
                "lichtpuntenField": [0],
                "loginnaamField": "string",
                "melderEmailField": "string",
                "melderNaamField": "string",
                "melderTelefoonField": "string",
                "meldingsnummerField": "string",
                "naderePlaatsbepalingField": "string",
                "omschrijvingField": "string",
                "straatnaamField": "string",
                "spoedField": True,
                "xCoordField": 0,
                "yCoordField": 0,
                "aanmaakDatumField": now,
                "adoptantnummerField": 0,
            }
        }


class Error(BaseModel):
    codeField: Optional[str]
    messageField: Optional[str]


class ServiceResult(BaseModel):
    codeField: Union[str, None]
    errorsField: Union[list[Error], dict[str, list], None]
    messageField: Union[str, None]


class MessagesField(BaseModel):
    string: list[str]


class ResponseBase(BaseModel):
    messagesField: Union[MessagesField, None]
    serviceResultField: Union[ServiceResult, None]


class ResponseOfInsert(ResponseBase):
    dataField: Union[Any, None]
    newIdField: Union[str, None]


class ResponseOfUpdate(ResponseBase):
    rowsUpdatedField: int


class MorMelding(BaseModel):
    datumAfhandelingField: Union[datetime, None]
    datumStatusWijzigingField: Union[datetime, None]
    morIdField: Union[str, None]
    msbIdField: Union[str, int, None]
    statusBerichtField: Union[str, None]
    statusField: Union[str, None]
    statusOmschrijvingField: Union[str, None]
    statusTemplateField: Union[str, None]


class MorMeldingenWrapper(BaseModel):
    MorMelding: Union[list[MorMelding], None]


class ResponseOfGetMorMeldingen(ResponseBase):
    morMeldingenField: Union[MorMeldingenWrapper, None]


class MorMeldingVolgenRequest(BaseModel):
    emailVolgerField: Union[str, None]
    morIdField: Union[str, None]
    toevoegenField: bool
