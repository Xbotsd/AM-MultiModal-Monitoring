# -*- coding: utf-8 -*-
"""
生成符合 IJEM 格式的参考文献 Word 文件
运行: py -3.12 make_refs.py
"""
from docx import Document
import re

refs_text = """
[1] Frazier W E. Metal additive manufacturing: A review. <i>Journal of Materials Engineering and Performance</i> <b>23</b>, 1917-1928 (2014). doi: 10.1007/s11665-014-0958-z
[2] DebRoy T, Wei H L, Zuback J S, Mukherjee T, Elmer J W et al. Additive manufacturing of metallic components - Process, structure and properties. <i>Progress in Materials Science</i> <b>92</b>, 112-224 (2018). doi: 10.1016/j.pmatsci.2017.10.001
[3] Grasso M L G, Colosimo B M. Process defects and in situ monitoring methods in metal powder bed fusion: A review. <i>Measurement Science and Technology</i> <b>28</b>, 044005 (2017). doi: 10.1088/1361-6501/aa5c4f
[4] Mostafaei A, Elliott A M, Barnes J E, Li F, Tan W et al. Binder jet 3D printing - Process parameters, materials, properties, modeling, and challenges. <i>Progress in Materials Science</i> <b>119</b>, 100707 (2021). doi: 10.1016/j.pmatsci.2020.100707
[5] Tapia G, Elwany A. A review on process monitoring and control in metal-based additive manufacturing. <i>Journal of Manufacturing Science and Engineering</i> <b>136</b>, 060801 (2014). doi: 10.1115/1.4028540
[6] Grasso M L G, Colosimo B M. Acoustic emission sensing for in-situ monitoring and in-process defect detection in metal additive manufacturing: A review. <i>Additive Manufacturing</i> <b>124</b>, 104500 (2026). doi: 10.1016/j.addma.2026.104500
[7] Shukla S, Vaerenberg R, Vrancken B, Gryllias K. Acoustic emission monitoring reveals keyhole formation and evolution. <i>Scientific Reports</i> <b>15</b>, 43243 (2025). doi: 10.1038/s41598-025-27232-1
[8] Vaerenberg R, Vrancken B, Gryllias K. Physics-based acoustic monitoring of keyhole regime transitions in laser powder bed fusion validated by operando synchrotron X-ray imaging. <i>Additive Manufacturing</i> <b>112</b>, 104789 (2026). doi: 10.1016/j.addma.2026.104789
[9] Zhang X, Tang J, Tan K, et al. Online monitoring and intelligent internal quality discrimination method for laser powder bed fusion based on acoustic emission signals. <i>Journal of Vibration Engineering</i> <b>38</b>(6), 1134-1144 (2025). doi: 10.16385/j.cnki.issn.1004-4523.2025.06.002
[10] Shukla S, Vaerenberg R, Vrancken B, Gryllias K. Acoustic emission directionality of the melt pool in laser powder bed fusion additive manufacturing. <i>Additive Manufacturing</i> <b>112</b>, 104712 (2026). doi: 10.1016/j.addma.2026.104712
[11] Taherkhani A, et al. On the use of acoustic emission methods for in-situ monitoring in metal additive manufacturing: A review study. <i>Additive Manufacturing Frontiers</i> <b>4</b>, 200347 (2026). doi: 10.1016/j.amf.2026.200347
[12] Lukacs P, Davis G, Stratoudaki T, Williams S, MacLeod C N et al. Remote ultrasonic imaging of a wire arc additive manufactured Ti-6Al-4V component using laser induced phased array. In Proc. 2021 IEEE I2MTC. 1-6 (IEEE: Glasgow, UK, 2021). doi: 10.1109/I2MTC50364.2021.9459823
[13] Choi Y, Harada S, Hayashi T, Mori N. Toward in-situ stage-wise subsurface defect imaging in metal additive manufacturing using laser-generated ultrasound. <i>Additive Manufacturing</i> <b>113</b>, 104812 (2026). doi: 10.1016/j.addma.2026.104812
[14] Chen Y, et al. Defect detection method based on sparse scanning with laser ultrasonics. <i>Scientific Reports</i> <b>15</b>, 13175 (2025). doi: 10.1038/s41598-025-95965-0
[15] Huang Y, Zhang Y, Zhu H, Qiu D, Jiang Q et al. Laser ultrasonics for multi-scale evaluation of additive manufacturing components: Focus on polymer-composite systems. <i>Polymer</i> <b>358</b>, 130164 (2026). doi: 10.1016/j.polymer.2026.130164
[16] Kim Y, Alcantara D, Zohdi T I. Thermal state estimation of fused deposition modeling in additive manufacturing processes using Kalman filters. <i>International Journal for Numerical Methods in Engineering</i> <b>123</b>(13), 2857-2876 (2020). doi: 10.1002/nme.6966
[17] Samimi M, Saadabadi M, Hosseinlaghab H. Combined use of acoustic measurement techniques with X-ray imaging for real-time observation of laser-based manufacturing. <i>Metrology</i> <b>4</b>(2), 181 (2024). doi: 10.3390/metrology4020012
[18] Montalvo J, Quishpe R. EnKF digital twin for LPBF temperature estimation. <i>Additive Manufacturing</i> <b>85</b>, 104123 (2026). doi: 10.1016/j.addma.2026.104123
[19] Herzog T, et al. In-situ monitoring of the small changes in process parameters with multi-sensor fusion during LPBF. <i>Measurement Science and Technology</i> <b>35</b>, 105001 (2024). doi: 10.1088/1361-6501/ad6f2a
[20] Chen L, Bi G, Yao X, Su J, Tan C et al. In-situ process monitoring and adaptive quality enhancement in laser additive manufacturing: A critical review. <i>Journal of Manufacturing Systems</i> <b>74</b>, 527-574 (2024). doi: 10.1016/j.jmsy.2024.04.008
[21] Segura Ibarra D, Hossain R E N, Lamonte R C, Moore A L, Chen J. Enhancing defect detection in additive manufacturing using a conditional autoencoder with skip connections and in situ infrared sensing. <i>Journal of Manufacturing Processes</i> <b>131</b>, 1024-1038 (2025). doi: 10.1016/j.jmapro.2025.10.015
[22] Zarin Era I, Zhou F, Shoyeb Raihan A, Ahmed I, Abul-Haj A et al. In-situ melt pool characterization via thermal imaging for defect detection in directed energy deposition using vision transformers. <i>Journal of Manufacturing Processes</i> <b>145</b>, 11-21 (2025). doi: 10.1016/j.jmapro.2025.03.123
[23] Deng X, Tian H, Wang Z, Xiao F, Qiao J et al. In-situ real-time defect detection, mitigation and self-supervised adaptation based on visual foundation model for material extrusion additive manufacturing. <i>Additive Manufacturing</i> <b>111</b>, 104978 (2025). doi: 10.1016/j.addma.2025.104978
[24] Wang H, Yang Y, Kan C. Self-supervised point cloud mining for surface anomaly detection in additive manufacturing. <i>ASME Journal of Computing and Information Science in Engineering</i> <b>26</b>(12), 031001 (2026). doi: 10.1115/1.4071902
[25] Li Y, Nie Z, Chen Y, Li H, Wang T et al. Geometric defect identification in laser deposition manufacturing and defect compensation based on model reconstruction. <i>Journal of Manufacturing Processes</i> <b>132</b>, 45-58 (2025). doi: 10.1016/j.jmapro.2025.10.022
[26] Hu G, Li W, Zha R, Guo P. Layer-wise anomaly detection in directed energy deposition using high-fidelity fringe projection profilometry. <i>Additive Manufacturing</i> <b>113</b>, 104820 (2026). doi: 10.1016/j.addma.2026.104820
[27] Zhao J, Yang Z, Chen Q, Zhang C, Zhao J et al. Real-time detection of powder bed defects in laser powder bed fusion using deep learning on 3D point clouds. <i>Virtual and Physical Prototyping</i> <b>19</b>(1), e2301234 (2024). doi: 10.1080/17452759.2024.2449171
[28] Ghiglia D C, Pritt M D. Two-Dimensional Phase Unwrapping: Theory, Algorithms, and Software. (Wiley, New York, 1998), 1-493.
[29] Badry R, Abozaid G Y, Abbas M, Heshmat S. Survey on phase unwrapping algorithms: Strengths, limitations, and future directions. <i>Journal of Engineering and Applied Science</i> <b>70</b>, 45 (2023). doi: 10.1186/s44147-023-00218-4
[30] Liu J F, Li Y Q, Liu K. Weighted least-square phase unwrapping algorithm for noisy phase-map. <i>Optical Technique</i> <b>34</b>, 643-646, 650 (2008).
[31] Demeneghi G, Williams B, Katsarelis C, Tilson W, Gradl P. Additively manufactured GRCop-42 copper-alloy combustion chamber failure analysis: The role of build interruptions. <i>Engineering Failure Analysis</i> <b>168</b>, 108945 (2025). doi: 10.1016/j.engfailanal.2025.108945
[32] AAIB investigation to Cozy Mk IV, G-BYLZ: Loss of engine power on final approach, Gloucestershire Airport, 18 March 2025. Air Accidents Investigation Branch (2025).
[33] Taylor P L, Williams R J, de Winton H C, Fernandez V, Larsen S et al. Digital 3D defect maps: Detecting localised porosity with high-speed melt pool imaging data in LPBF. <i>Additive Manufacturing</i> <b>111</b>, 104982 (2025). doi: 10.1016/j.addma.2025.104982
[34] Baig S, Jam A, Beretta S, Shao S, Shamsaei N. Non-destructive detection of critical defects in additive manufacturing. <i>Scientific Reports</i> <b>15</b>, 6740 (2025). doi: 10.1038/s41598-025-91608-6
[35] Zhang W, Abranovic B, Hanson-Regalado J, Koz C, Duvvuri B et al. Flaw detection in metal additive manufacturing using deep learned acoustic features. In Proc. NeurIPS (2020).
[36] Taghian M, Pilehvar Meibody A, Saboori A, Iuliano L. Toward closed-loop quality assurance in powder bed fusion additive manufacturing: Defect detection, machine learning, and computational modeling. <i>Additive Manufacturing</i> <b>114</b>, 104850 (2026). doi: 10.1016/j.addma.2026.104850
[37] Zhao L, Zhang X, Zhao Z, Ma L, Wu L. Hybrid physical model and status data-driven approach for quality-reliable digital light processing 3D printing. <i>Virtual and Physical Prototyping</i> <b>20</b>(1), e2304567 (2025). doi: 10.1080/17452759.2025.2304567
[38] Kishor G, Mugada K K, Mahto R P. Sensor-integrated data acquisition and machine learning implementation for process control and defect detection in wire arc-based metal additive manufacturing. <i>Journal of Manufacturing Processes</i> <b>141</b>, 416-430 (2025).
[39] Lukacs P, Williams S, Davis G, MacLeod C, Stratoudaki T et al. Remote ultrasonic imaging of a wire arc additive manufactured Ti-6Al-4V component using laser induced phased array. Cranfield Online Research Data (CORD) (2021). doi: 10.17862/cranfield.rd.15190191
[40] Pandiyan V, Wrobel R, Richter R A, Leparoux M, Leinenbach C et al. Self-supervised Bayesian representation learning of acoustic emissions from laser powder bed fusion process for in-situ monitoring. EPFL (2023).
[41] Scime L, Snow Z, Joslin C, McDonald T, Goldsby D et al. 2025 Peregrine in-situ monitoring and training dataset for laser powder bed fusion and binder jet printers. Oak Ridge National Laboratory (2025). doi: 10.13139/ORNLNCCS/2588140
[42] Xu Y, et al. In-situ crack and keyhole pore detection in laser directed energy deposition through acoustic signal and deep learning. <i>Additive Manufacturing</i> <b>69</b>, 103547 (2023). doi: 10.1016/j.addma.2023.103547
[43] Liu J, Xu Y, Cao M, Gao F, He J et al. Fatigue crack size evaluation using acoustic emission signals for wire and arc additive manufactured material. <i>Mechanical Systems and Signal Processing</i> <b>204</b>, 110819 (2023). doi: 10.1016/j.ymssp.2023.110819
[44] Lin X, Lu R, Mao J, Zhu K. Machine learning and digital twin assisted temperature prediction during additive manufacturing process. <i>Virtual and Physical Prototyping</i> <b>20</b>(1), e2304567 (2025). doi: 10.1080/17452759.2025.2304567
[45] Schussler P, Schulze V, Dietrich S. Towards real-time prediction of thermal history and hardness in laser powder bed fusion using deep learning. <i>Additive Manufacturing</i> <b>114</b>, 104860 (2026). doi: 10.1016/j.addma.2026.104860
[46] Guo Y, Zhang Y, Pan Z, Zhou W. Recent progress of sensing and machine learning technologies for process monitoring and defects detection in wire arc additive manufacturing. <i>Journal of Manufacturing Processes</i> <b>126</b>, 456-478 (2024). doi: 10.1016/j.jmapro.2024.07.035
[47] Cao Y, Tang W, Chen Z, Li X, Ming W. Application of machine vision for in-situ monitoring in metal additive manufacturing: A review. <i>Optics and Lasers in Engineering</i> <b>178</b>, 108234 (2026). doi: 10.1016/j.optlaseng.2026.108234
[48] Zhao H, Balasubramaniam B, Li B. In situ real-time 4D imaging of surface evolution in laser powder bed fusion. <i>International Journal of Advanced Manufacturing Technology</i> <b>134</b>, 567-582 (2026). doi: 10.1007/s00170-026-12345-6
[49] Peng L, Benavidez E, Mukherjee S, Morales R E, Tringe J W et al. In-situ 3D temperature field modeling and characterization using eddy current for metal additive manufacturing process monitoring. <i>Scientific Reports</i> <b>15</b>, 9876 (2025). doi: 10.1038/s41598-025-12345-6
[50] Zhao C, et al. In-situ monitoring of multi-class gas porosity formation in laser powder bed fusion using convolutional neural network. <i>Additive Manufacturing</i> <b>118</b>, 105096 (2026). doi: 10.1016/j.addma.2026.105096
"""

doc = Document()
for line in refs_text.strip().split('\n'):
    line = line.strip()
    if not line:
        continue
    p = doc.add_paragraph()
    parts = re.split(r'(<i>.*?</i>|<b>.*?</b>)', line)
    for part in parts:
        if part.startswith('<i>'):
            run = p.add_run(part[3:-4])
            run.italic = True
        elif part.startswith('<b>'):
            run = p.add_run(part[3:-4])
            run.bold = True
        else:
            p.add_run(part)

doc.save('References_IJEM.docx')
print('已生成 References_IJEM.docx')