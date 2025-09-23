from pydantic import BaseModel


class EmagAccountConfig(BaseModel):
    username: str
    password: str


class EmagConfig(BaseModel):
    main: EmagAccountConfig
    fbe: EmagAccountConfig
