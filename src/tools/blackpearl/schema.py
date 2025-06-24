"""Blackpearl API schemas.

This module defines the Pydantic models for Blackpearl API request and response validation.
"""
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, EmailStr

from datetime import datetime
from enum import Enum

class StatusAprovacaoEnum(str, Enum):
    NOT_REGISTERED = "NOT_REGISTERED"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"
    PENDING_REVIEW = "PENDING_REVIEW"
    VERIFYING = "VERIFYING"

class StatusNegociacaoEnum(str, Enum):
    PROPOSTA = "0"
    ANALISE = "1"
    RENEGOCIACAO = "2"
    REPROVADO = "3"
    APROVADO = "4"

class StatusPedidoEnum(str, Enum):
    ABERTO = "0"
    VENDA = "10"
    SEPARAR_ESTOQUE = "20"
    FATURAR = "50"
    FATURADO = "60"
    ENTREGA = "70"

class FreteModalidadeEnum(str, Enum):
    CIF = "0"
    FOB = "1"
    TERCEIROS = "2"
    TRANSPORTE_PROPRIO_REMETENTE = "3"
    TRANSPORTE_PROPRIO_DESTINATARIO = "4"
    SEM_FRETE = "9"

class RegiaoEnum(str, Enum):
    AC = "AC"
    AL = "AL"
    AP = "AP"
    AM = "AM"
    BA = "BA"
    CE = "CE"
    DF = "DF"
    ES = "ES"
    GO = "GO"
    MA = "MA"
    MT = "MT"
    MS = "MS"
    MG = "MG"
    PA = "PA"
    PB = "PB"
    PR = "PR"
    PE = "PE"
    PI = "PI"
    RJ = "RJ"
    RN = "RN"
    RS = "RS"
    RO = "RO"
    RR = "RR"
    SC = "SC"
    SP = "SP"
    SE = "SE"
    TO = "TO"
    NORTE = "N"
    NORDESTE = "NE"
    CENTRO_OESTE = "CO"
    SUDESTE = "SU"
    SUL = "S"

class TimeEnum(str, Enum):
    INDEFINIDO = "Indefinido"
    REDRAGON = "Redragon"
    OUTRAS_MARCAS = "Outras Marcas"
    KALKAN_KEYTIME = "Kalkan/Keytime"

class TipoImagemEnum(str, Enum):
    OUTROS = "OUTROS"
    TECNICA = "TECNICA"
    MARKETING = "MARKETING"

class Marca(BaseModel):
    id: int = Field(..., description="Unique identifier")
    nome: str = Field(..., max_length=255)
    logo: Optional[str] = Field(None, description="Logo URL")
    site: Optional[str] = Field(None, max_length=200, description="Manufacturer website")

class FamiliaDeProduto(BaseModel):
    id: int = Field(..., description="Unique identifier")
    codigo: int = Field(..., description="Product family code in Omie")
    nomeFamilia: str = Field(..., max_length=255, description="Family name")
    
class TipoOperacaoEnum(str, Enum):
    ONLINE = "Online"
    FISICA = "Física"
    HIBRIDA = "Híbrida"
    INDEFINIDO = "Indefinido"

class Cliente(BaseModel):
    id: Optional[int] = Field(None, description="Unique identifier")
    contatos: Optional[List[Union[int, Dict[str, Any]]]] = Field(None, description="Contacts list from API response")
    contatos_ids: Optional[List[int]] = Field(None, description="Contact IDs")
    vendedores: Optional[List[Union[int, Dict[str, Any]]]] = Field(None, description="Salesperson IDs")
    # telefone_comercial: Optional[str] = None
    tipo_operacao: Optional[TipoOperacaoEnum] = None
    numero_funcionarios: Optional[int] = None
    razao_social: Optional[str] = Field(None, max_length=255)
    nome_fantasia: Optional[str] = Field(None, max_length=255)
    cnpj_cpf: Optional[str] = Field(None, max_length=18)
    inscricao_estadual: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=500)
    endereco: Optional[str] = None
    endereco_numero: Optional[str] = Field(None, max_length=16)
    endereco_complemento: Optional[str] = Field(None, max_length=255)
    bairro: Optional[str] = Field(None, max_length=255)
    cidade: Optional[str] = Field(None, max_length=255)
    estado: Optional[str] = Field(None, max_length=2)
    cep: Optional[str] = Field(None, max_length=9)
    codigo_cliente_omie: Optional[int] = Field(None, description="Omie client code")
    status_aprovacao: Optional[StatusAprovacaoEnum] = None
    valor_limite_credito: Optional[int] = None
    data_aprovacao: Optional[datetime] = None
    detalhes_aprovacao: Optional[str] = None
    data_registro: Optional[datetime] = None
    ultima_atualizacao: Optional[datetime] = None
    tabela_preco: Optional[int] = None
    telefone1_ddd: Optional[str] = None
    telefone1_numero: Optional[str] = None
    telefone2_ddd: Optional[str] = None
    telefone2_numero: Optional[str] = None
    valor_limite_credito: Optional[int] = None

class Contato(BaseModel):
    id: Optional[int] = Field(None, description="Unique identifier")
    nome: Optional[str] = None
    telefone: Optional[str] = None
    wpp_session_id: Optional[str] = None
    ativo: Optional[bool] = None
    data_registro: Optional[datetime] = None
    status_aprovacao: Optional[StatusAprovacaoEnum] = None
    data_aprovacao: Optional[datetime] = None
    detalhes_aprovacao: Optional[str] = None
    ultima_atualizacao: Optional[datetime] = None

class Vendedor(BaseModel):
    id: int = Field(..., description="Unique identifier")
    codigo: int = Field(..., description="Omie salesperson code")
    nome: str = Field(..., max_length=255)
    apelido: Optional[str] = Field(None, max_length=255)
    email: EmailStr = Field(..., max_length=254)
    telefone: Optional[str] = Field(None, max_length=20)
    inativo: bool

class Precificacao(BaseModel):
    """Estrutura de precificação do produto"""
    ipi: str 
    st: str 
    custo: str 
    lucro: str 
    valor_venda: str 
    valor_venda_sem_impostos: str 
    comissao: str 
    desconto_maximo: str 

class Produto(BaseModel):
    id: int = Field(..., description="Unique identifier")
    marca: Marca
    familia: FamiliaDeProduto
    codigo_produto: int = Field(..., description="Product code in Omie")
    inativo: bool
    ean: Optional[str] = Field(None, max_length=64)
    codigo: Optional[str] = Field(None, max_length=64)
    descricao: Optional[str] = Field(None, max_length=255)
    descr_detalhada: Optional[str]
    unidade: Optional[str] = Field(None, max_length=32)
    # valor_unitario: float
    peso_bruto: float
    peso_liq: float
    largura: float
    altura: float
    profundidade: float
    cfop: Optional[str] = Field(None, max_length=32)
    ncm: Optional[str] = Field(None, max_length=32)
    especificacoes: Optional[str]
    marketing_info: Optional[str]
    # imagem = Optional[str] = Field(None, max_length=255)
    manual_tecnico: Optional[str] = Field(None, max_length=255)
    precificacao: Optional[Precificacao] = None
    estoque: int
    

class ItemDePedido(BaseModel):
    id: int = Field(..., description="Unique identifier")
    quantidade: int = Field(..., ge=0)
    valor_unitario_currency: str
    valor_unitario: str = Field(..., pattern=r'^-?\d{0,10}(?:\.\d{0,2})?$')
    desconto_currency: str
    desconto: str = Field(..., pattern=r'^-?\d{0,10}(?:\.\d{0,2})?$')
    porcentagem_desconto: float
    valor_total_currency: str
    valor_total: str = Field(..., pattern=r'^-?\d{0,10}(?:\.\d{0,2})?$')
    codigo_item_integracao: Optional[str] = Field(None, max_length=64)
    pedido: int
    produto: int

class ItemDePedidoCreate(BaseModel):
    quantidade: int = Field(..., ge=1) # Must have quantity
    valor_unitario: str = Field(..., pattern=r'^-?\d{0,10}(?:\.\d{0,2})?$')
    desconto: Optional[str] = Field(None, pattern=r'^-?\d{0,10}(?:\.\d{0,2})?$')
    porcentagem_desconto: Optional[float] = Field(0.0, ge=0.0)
    pedido: int # Must link to an order
    produto: int # Must link to a product

class ItemDePedidoUpdate(BaseModel):
    quantidade: Optional[int] = Field(None, ge=1)
    valor_unitario: Optional[str] = Field(None, pattern=r'^-?\d{0,10}(?:\.\d{0,2})?$')
    porcentagem_desconto: Optional[float] = Field(None, ge=0.0)

class PedidoDeVenda(BaseModel):
    id: int = Field(..., description="Unique identifier")
    cliente_detalhes: Optional[Dict[str, Any]] = Field(None, description="Detailed client information from API response")
    status_negociacao: StatusNegociacaoEnum
    status_pedido: StatusPedidoEnum
    observacoes: Optional[str]
    codigo_pedido: int = Field(..., description="Order code in Omie")
    codigo_pedido_integracao: Optional[str] = Field(None, max_length=16)
    data_emissao: datetime
    data_aprovacao: Optional[datetime]
    frete_modalidade: FreteModalidadeEnum
    cancelado: bool
    cliente: int
    pagamento: Optional[int]
    transportadora: Optional[int]
    vendedor: List[int]

class PedidoDeVendaCreate(BaseModel):
    cliente: int # Required
    vendedor: Optional[List[int]] = Field(None, description="Associate salesperson IDs") # Often required or context-based
    pagamento: Optional[int] = Field(None, description="Payment condition ID") # Often required
    frete_modalidade: Optional[FreteModalidadeEnum] = Field(None, description="Shipping mode") # Often required
    transportadora: Optional[int] = Field(None, description="Carrier ID") # Required depending on frete_modalidade?
    observacoes: Optional[str] = Field(None, description="Order observations")

class PedidoDeVendaUpdate(BaseModel):
    status_negociacao: Optional[StatusNegociacaoEnum] = None
    status_pedido: Optional[StatusPedidoEnum] = None
    observacoes: Optional[str] = None
    pagamento: Optional[int] = None
    frete_modalidade: Optional[FreteModalidadeEnum] = None
    transportadora: Optional[int] = None
    vendedor: Optional[List[int]] = None
    cancelado: Optional[bool] = None

class RegraDeFrete(BaseModel):
    id: int = Field(..., description="Unique identifier")
    regiao: RegiaoEnum
    cidade: Optional[str] = Field(None, max_length=128)
    valor_minimo_comum_currency: str
    valor_minimo_comum: str = Field(..., pattern=r'^-?\d{0,10}(?:\.\d{0,2})?$')
    transportadora_comum: Optional[str] = Field(None, max_length=64)
    observacoes_comum: Optional[str]
    valor_minimo_autocare_currency: str
    valor_minimo_autocare: str = Field(..., pattern=r'^-?\d{0,10}(?:\.\d{0,2})?$')
    transportadora_autocare: Optional[str] = Field(None, max_length=64)
    observacoes_autocare: Optional[str]

class RegraDeNegocio(BaseModel):
    id: int = Field(..., description="Unique identifier")
    titulo: str = Field(..., max_length=64)
    regra: str
    ativo: bool