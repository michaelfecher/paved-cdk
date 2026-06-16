"""paved-cdk — paved-road AWS CDK constructs for Data Scientists."""

from .account import PlatformAccount
from .compute import SecureLambda, SecureLambdaProps
from .config import PlatformConfig, PlatformConfigError
from .constructs import SecureDataApi, SecureDataApiProps
from .environment import PlatformEnvironment
from .registry import DEFAULT_REGISTRY, AccountRegistry
from .stacks import PlatformStack

__version__ = "0.1.0"

__all__ = [
    "PlatformStack",
    "PlatformEnvironment",
    "PlatformConfig",
    "PlatformConfigError",
    "PlatformAccount",
    "AccountRegistry",
    "DEFAULT_REGISTRY",
    # Catalog bricks (also available namespaced: paved_cdk.storage / paved_cdk.compute)
    "SecureDataApi",
    "SecureDataApiProps",
    "SecureLambda",
    "SecureLambdaProps",
]
