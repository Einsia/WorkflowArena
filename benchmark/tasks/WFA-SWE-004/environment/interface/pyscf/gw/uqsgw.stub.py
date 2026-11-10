# 接口说明（仅签名与文档字符串，函数体已省略）。此文件在起点仓库中不存在，需要新建。
"""
Spin-unrestricted quasiparticle self-consistent GW method based on the analytic continuation scheme.

References:
    J. Lei and T. Zhu, J. Chem. Phys. 157, 214114 (2022)
    T. Zhu and G.K.-L. Chan, J. Chem. Theory. Comput. 17, 727-741 (2021)
    Phys. Rev. B 76, 165106 (2007)
    J. Chem. Theory. Comput. 12, 2528-2541 (2016)
"""

def kernel(gw):
    ...

class UQSGW(UGWAC):

    def __init__(self, mf, frozen=None, auxbasis=None):
        ...

    def dump_flags(self):
        ...

    def dump_chk(self):
        ...

    def kernel(self):
        """Run a spin-unrestricted quasiparticle self-consistent GW calculation."""
        ...
