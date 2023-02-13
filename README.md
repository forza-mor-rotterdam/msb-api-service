
# Rest API interface for MSB 📝  
Endpoints are based on the existing external SOAP interface for MSB  
## Endpoints


## Get Started 🚀  
To get started, install Docker  

## Prebuilt Components/Templates 🔥  
You can checkout prebuilt components and templates by clicking on the menu icon
on the top left corner of the navbar.
    
## Save Readme ✨  
Once you're done, click on the save button to directly save your Readme to your
project's root directory!
 
## API Reference

### Create incident 

```http
  POST /AanmakenMelding/
```  
| Parameter | Type     | Reuired    |
| :--------------------------- | :------- | :------- |
| `aanvullendeInformatieField` | `string` | False
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
  GET /AanmakenMelding/
```  
| Parameter | Type     | Reuired    |
| :--------------------------- | :------- | :------- |
| `dagenField` | `float` | True
| `morIdField` | `string` |  False



