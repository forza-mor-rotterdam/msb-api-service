from pydantic import BaseModel
from typing import Union, Any, Optional
from datetime import datetime


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
    lichtpuntenField: Union[list[str], None]
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