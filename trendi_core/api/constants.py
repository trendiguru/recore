from ..master_constants import ImageStatus


products_per_ip_pid = {'default':
                           {'default': 'amazon_US', 'US': 'amazon_US', 'KR': 'GangnamStyle', 'DE': 'amazon_DE'},
                       'fashionseoul':
                           {'default': 'GangnamStyle', 'KR': 'GangnamStyle'},
                       '5767jA8THOn2J0DD':
                           {'default': 'GangnamStyle', 'KR': 'GangnamStyle'},
                       'RecruitPilot':
                           {'default': 'recruit'},
                       'recruit-pilot':
                           {'default': 'recruit'},
                       '6t50LSJxeNEkQ42p':
                           {'default': 'recruit'},
                       'xuSiNIs695acaHPE':
                           {'default': 'amaze'},
                       "Rob's Shelter":
                           {'default': 'amazon_US'},
                       "robsdemartino@yahoo.it":
                           {'default': 'amazon_US'},
                       "mz1_ND":
                           {'default': 'amazon_US', 'US': 'amazon_US'},
                       "6nGzEP7cp5s957P4":
                           {'default': 'shopstyle_DE'},
                       "2DqGp6fum7jiv2B6":
                           {'default': 'amazon_US'},
                       "sg3SH5yif242E5jL":
                           {'default': 'amazon_US'},
                       "Y8Y4jENvaJ2Lsklz":
                           {'default': 'shopstyle_US'},
                       "2Ldy4i23piqQG73n":
                           {'default': 'shopstyle_DE'}}

map_to_client = {"nd":
                     {ImageStatus.NEW_RELEVANT: False,
                      ImageStatus.NEW_NOT_RELEVANT: False,
                      ImageStatus.ADD_COLLECTION: False,
                      ImageStatus.RENEW_SEGMENTATION: True,
                      ImageStatus.IN_PROGRESS: True,
                      ImageStatus.READY: True,
                      ImageStatus.NOT_RELEVANT: False},
                 "pd":
                     {ImageStatus.NEW_RELEVANT: False,
                      ImageStatus.NEW_NOT_RELEVANT: False,
                      ImageStatus.ADD_COLLECTION: False,
                      ImageStatus.RENEW_SEGMENTATION: True,
                      ImageStatus.IN_PROGRESS: False,
                      ImageStatus.READY: True,
                      ImageStatus.NOT_RELEVANT: False}}
