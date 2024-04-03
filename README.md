
# Rest API interface for MSB
Endpoints are based on the existing external SOAP interface for MSB(Meldingen Systeem Buitenruimte) for the municipality Rotterdam, the Netherlands


## Tech Stack
[Uvicorn](https://www.uvicorn.org/), [FastAPI](https://fastapi.tiangolo.com/), [Zeep SOAP client](https://docs.python-zeep.org/en/master/index.html)

## Get Started 🚀
To get started, install [Docker](https://www.docker.com/)

### Create .env.local from .env
~~~bash
    cp .env .env.local
~~~


### Build and run Docker container
~~~bash
    docker compose up
~~~

This will start a webserver on http://localhost:8001,
So, with a curl call like below
~~~bash
    curl "http://localhost:8001/v1/MeldingenOpvragen/?dagenField=10"
~~~
You should get some incidents

### OpenApi Docs
http://localhost:8001/docs

## API Reference📝

### Create incident

```http
  POST /AanmakenMelding/
```
| Parameter | Type     | Required    |
| :--------------------------- | :------- | :------- |
| `aanvullendeInformatieField` | `string` | False
| `aanvullendeVragenField` | `[{question: string, answers: string[]}]` | False
| `bijlagenField` | `Bestand[]` |  False
| `fotosField` | `string[]` | False
| `huisnummerField` | `string` | False
| `kanaalField` | `string` | False
| `onderwerpField` | `string` | False
| `lichtpuntenField` | `string[]` | False
| `loginnaamField` | `string` | False
| `melderEmailField` | `string` | False
| `melderNaamField` | `string` | False
| `melderTelefoonField` | `string` | False
| `meldingsnummerField` | `string` | False
| `naderePlaatsbepalingField` | `string` | False
| `omschrijvingField` | `string` | False
| `straatnaamField` | `string` | False
| `spoedField` | `bool` | True
| `xCoordField` | `float` | True
| `yCoordField` | `float` | True

### Follow incident

```http
  PATCH /MeldingVolgen/
```
| Parameter | Type     | Reuired    |
| :--------------------------- | :------- | :------- |
| `emailVolgerField` | `string` | False
| `morIdField` | `string` |  False
| `toevoegenField` | `bool` | True

### Get all incidents

```http
  GET /MeldingenOpvragen/
```
| Parameter | Type     | Reuired    |
| :--------------------------- | :------- | :------- |
| `dagenField` | `float` | True
| `morIdField` | `string` |  False
