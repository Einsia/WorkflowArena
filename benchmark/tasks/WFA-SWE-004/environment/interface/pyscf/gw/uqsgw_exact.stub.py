# 接口说明（仅签名与文档字符串，函数体已省略）。此文件在起点仓库中不存在，需要新建。
"""
Spin-unrestricted quasiparticle self-consistent GW method based on the fully analytic scheme.

References:
    J. Chem. Theory. Comput. 12, 2528-2541 (2016)
    J. Chem. Theory Comput. 9, 1, 232-246 (2013)
"""

def kernel(gw):
    ...

class UQSGWExact(UGWAC):

    def __init__(self, mf, auxbasis=None):
        ...

    def dump_flags(self, verbose=None):
        ...

    def kernel(self):
        ...
