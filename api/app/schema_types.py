from pydantic import BaseModel, validator
from typing import Union, Any, Optional
from datetime import datetime
import pytz


class Bestand(BaseModel):
    bytesField: Union[str, None]
    mimeTypeField: Union[str, None]
    naamField: Union[str, None]


class MorMeldingAanmakenRequest(BaseModel):
    aanvullendeInformatieField: Union[str, None]
    bijlagenField: Union[list[Bestand], None]
    fotosField: Union[list[str], None]
    huisnummerField: Union[str, None]
    kanaalField: Union[str, None]
    onderwerpField: Union[str, None]
    lichtpuntenField: Union[list[int], None]
    loginnaamField: Union[str, None]
    melderEmailField: Union[str, None]
    melderNaamField: Union[str, None]
    melderTelefoonField: Union[str, None]
    meldingsnummerField: Union[str, None]
    naderePlaatsbepalingField: Union[str, None]
    omschrijvingField: Union[str, None]
    straatnaamField: Union[str, None]
    spoedField: bool
    xCoordField: float
    yCoordField: float
    aanmaakDatumField: Union[datetime, None]
    adoptantnummerField: Union[int, None]

    @validator("aanmaakDatumField", pre=False)
    def parse_aanmaakDatumField(cls, value):
        return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        now = datetime.now(pytz.timezone("Europe/Amsterdam")).isoformat()
        schema_extra = {
            'example':
                {
                "aanvullendeInformatieField": "string",
                "bijlagenField": [
                    {
                    "bytesField": "base64_string",
                    "mimeTypeField": "string",
                    "naamField": "string"
                    }
                ],
                "fotosField": [
                    "base64_string"
                ],
                "huisnummerField": "string",
                "kanaalField": "string",
                "onderwerpField": "string",
                "lichtpuntenField": [
                    0
                ],
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
                "adoptantnummerField": 0
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
    msbIdField: Union[str, None]
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