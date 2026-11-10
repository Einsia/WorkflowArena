# 接口说明（仅签名与文档字符串，函数体已省略）。此文件在起点仓库中不存在，需要新建。
"""
Spin-unrestricted eigenvalue self-consistent GW method based on the analytic continuation scheme.

References:
    Phys. Rev. B 76, 165106 (2007)
    J. Chem. Theory. Comput. 12, 2528-2541 (2016)
"""

def kernel(gw):
    ...

class UEVGW(UGWAC):

    def __init__(self, mf, frozen=None, auxbasis=None):
        ...

    def dump_flags(self, verbose=None):
        ...

    def kernel(self):
        """Run a spin-unrestricted eigenvalue-self-consistent GW calculation."""
        ...
