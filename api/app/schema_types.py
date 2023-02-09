from pydantic import BaseModel
from typing import Union, Any, cast, Optional
from datetime import datetime


class Bestand(BaseModel):
    bytesField: Union[str, None]
    mimeTypeField: Union[str, None]
    naamField: Union[str, None]


class MorMeldingAanmakenRequest(BaseModel):
    aanvullendeInformatieField: Union[str, None] = "my_aanvullendeInformatie"
    bijlagenField: Union[list[Bestand], None] = [cast(Bestand, {"bytesField": "base64_string_voorbeeld_1", "mimeTypeField": "text/txt", "naamField": "bestandsnaam"})]
    fotosField: Union[list[str], None]# = ["base64_string_voorbeeld_1", "base64_string_voorbeeld_2"]
    huisnummerField: Union[str, None] = "4"
    kanaalField: Union[str, None] = "238"
    onderwerpField: Union[str, None] = "MeldR onderwerp"
    lichtpuntenField: Union[list[str], None] = ["001", "002"]
    loginnaamField: Union[str, None] = "foo"
    melderEmailField: Union[str, None] = "foo@bar.org"
    melderNaamField: Union[str, None] = "foo"
    melderTelefoonField: Union[str, None] = "0123456789"
    meldingsnummerField: Union[str, None] = "3000-000052"
    naderePlaatsbepalingField: Union[str, None] = "my_naderePlaatsbepaling"
    omschrijvingField: Union[str, None] = "my_omschrijving"
    straatnaamField: Union[str, None] = "COOLSINGEL"
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