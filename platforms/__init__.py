"""
platforms/__init__.py - Adaptadores de plataformas de freelas nacionais e internacionais
"""

from platforms.noventa_nove_freelas import NoventaNoveFreelas
from platforms.workana import WorkanaPlatform
from platforms.remoteok import RemoteOKPlatform
from platforms.weworkremotely import WeWorkRemotelyPlatform
from platforms.remotive import RemotivePlatform
from platforms.freelancer import FreelancerPlatform
from platforms.linkedin import LinkedInPlatform

__all__ = [
    "NoventaNoveFreelas",
    "WorkanaPlatform",
    "RemoteOKPlatform",
    "WeWorkRemotelyPlatform",
    "RemotivePlatform",
    "FreelancerPlatform",
    "LinkedInPlatform"
]
