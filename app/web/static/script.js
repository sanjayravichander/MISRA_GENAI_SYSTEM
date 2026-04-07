"use strict";
/* =========================================================
   SRM Technologies — MISRA Compliance Reviewer  script.js
   ========================================================= */

const IS_RESULTS = typeof window.MISRA_RUN_ID !== "undefined";
IS_RESULTS ? initResultsPage() : initIndexPage();

/* ============================================================
   RULES DATA
   ============================================================ */
var RULES_DATA = [{ "id": "9.1", "sev": "M", "full_sev": "MISRA-M", "warnings": ["2883", "2961", "2962", "2971", "2972"], "is_dir": false }, { "id": "1.1", "sev": "R", "full_sev": "Dir-R", "warnings": ["0180", "0202", "0284", "0285", "0286", "0287", "0288", "0289", "0292", "0299", "0320", "0371", "0372", "0375", "0380", "0388", "0390", "0391", "0392", "0410", "0581", "0604", "0609", "0611", "0612", "0614", "0617", "0618", "0634", "0639", "0647", "0715", "0739", "0810", "0828", "0850", "0857", "0858", "0859", "0875", "0930", "1011", "1018", "1027", "1030", "1031", "1053", "1054", "1055", "1056", "2855", "2856", "2857", "2860", "2861", "2862", "2895", "2896", "2897", "3116"], "is_dir": true }, { "id": "12.5", "sev": "M", "full_sev": "MISRA-M", "warnings": ["1321"], "is_dir": false }, { "id": "4.1", "sev": "R", "full_sev": "Dir-R", "warnings": ["2791", "2792", "2801", "2802", "2811", "2812", "2821", "2822", "2831", "2832", "2841", "2842", "2845", "2846", "2847", "2871", "2872", "2877"], "is_dir": true }, { "id": "13.6", "sev": "M", "full_sev": "MISRA-M", "warnings": ["3307"], "is_dir": false }, { "id": "4.2", "sev": "A", "full_sev": "Dir-A", "warnings": ["1003", "1006"], "is_dir": true }, { "id": "17.3", "sev": "M", "full_sev": "MISRA-M", "warnings": ["3335"], "is_dir": false }, { "id": "4.3", "sev": "R", "full_sev": "Dir-R", "warnings": ["3006"], "is_dir": true }, { "id": "17.4", "sev": "M", "full_sev": "MISRA-M", "warnings": ["0745", "2887", "2888", "3113", "3114"], "is_dir": false }, { "id": "4.6", "sev": "A", "full_sev": "Dir-A", "warnings": ["5209"], "is_dir": true }, { "id": "17.6", "sev": "M", "full_sev": "MISRA-M", "warnings": ["0460", "0461", "0462", "0463", "1058", "1059"], "is_dir": false }, { "id": "4.9", "sev": "A", "full_sev": "Dir-A", "warnings": ["3453"], "is_dir": true }, { "id": "19.1", "sev": "M", "full_sev": "MISRA-M", "warnings": ["0681", "2776", "2777"], "is_dir": false }, { "id": "4.10", "sev": "R", "full_sev": "Dir-R", "warnings": ["883"], "is_dir": true }, { "id": "21.13", "sev": "M", "full_sev": "MISRA-M", "warnings": ["2796", "2797"], "is_dir": false }, { "id": "4.14", "sev": "R", "full_sev": "Dir-R", "warnings": ["2956"], "is_dir": true }, { "id": "21.17", "sev": "M", "full_sev": "MISRA-M", "warnings": ["2835", "2836"], "is_dir": false }, { "id": "21.18", "sev": "M", "full_sev": "MISRA-M", "warnings": ["2840", "2841", "2842"], "is_dir": false }, { "id": "21.19", "sev": "M", "full_sev": "MISRA-M", "warnings": ["1492", "1493", "1498"], "is_dir": false }, { "id": "21.20", "sev": "M", "full_sev": "MISRA-M", "warnings": ["2681", "2682"], "is_dir": false }, { "id": "22.5", "sev": "M", "full_sev": "MISRA-M", "warnings": ["1485", "1486"], "is_dir": false }, { "id": "1.3", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0160", "0161", "0162", "0163", "0164", "0165", "0166", "0167", "0168", "0169", "0170", "0171", "0172", "0173", "0174", "0175", "0176", "0177", "0178", "0179", "0184", "0185", "0186", "0190", "0191", "0192", "0193", "0194", "0195", "0196", "0197", "0198", "0199", "0200", "0201", "0203", "0204", "0206", "0207", "0208", "0235", "0275", "0301", "0302", "0304", "0307", "0309", "0337", "0400", "0401", "0402", "0403", "0475", "0543", "0544", "0545", "0602", "0623", "0625", "0626", "0630", "0632", "0636", "0654", "0658", "0661", "0667", "0668", "0672", "0676", "0678", "0680", "0706", "0745", "0777", "0779", "0809", "0813", "0814", "0836", "0837", "0848", "0853", "0854", "0864", "0865", "0867", "0872", "0874", "0885", "0887", "0888", "0914", "0915", "0942", "1331", "1332", "1333", "1509", "1510", "2800", "2810", "2820", "2830", "2840", "3113", "3114", "3239", "3311", "3312", "3319", "3320", "3437", "3438"], "is_dir": false }, { "id": "2.1", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0594", "1460", "1503", "2742", "2744", "2880", "2882", "3219"], "is_dir": false }, { "id": "2.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2980", "2981", "2982", "2983", "2995", "2996", "3110", "3112", "3404", "3422", "3423", "3424", "3425", "3426", "3427"], "is_dir": false }, { "id": "3.1", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3108", "5133"], "is_dir": false }, { "id": "3.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["5134"], "is_dir": false }, { "id": "5.1", "sev": "R", "full_sev": "MISRA-R", "warnings": ["777"], "is_dir": false }, { "id": "5.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["779"], "is_dir": false }, { "id": "5.3", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2547", "3334"], "is_dir": false }, { "id": "5.4", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0778", "0788", "0789"], "is_dir": false }, { "id": "5.5", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0784", "0785", "0786", "0787"], "is_dir": false }, { "id": "5.6", "sev": "R", "full_sev": "MISRA-R", "warnings": ["780", "782", "1506", "1507", "1508", "3448"], "is_dir": false }, { "id": "5.7", "sev": "R", "full_sev": "MISRA-R", "warnings": ["1750"], "is_dir": false }, { "id": "5.8", "sev": "R", "full_sev": "MISRA-R", "warnings": ["1525", "1526"], "is_dir": false }, { "id": "6.1", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0634", "0635"], "is_dir": false }, { "id": "6.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3660", "3665"], "is_dir": false }, { "id": "7.1", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0336", "0339"], "is_dir": false }, { "id": "7.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["1281"], "is_dir": false }, { "id": "7.3", "sev": "R", "full_sev": "MISRA-R", "warnings": ["1280"], "is_dir": false }, { "id": "7.4", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0752", "0753"], "is_dir": false }, { "id": "8.1", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2050", "2051"], "is_dir": false }, { "id": "8.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["1335", "1336", "3001", "3002", "3007"], "is_dir": false }, { "id": "8.3", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0624", "1330", "3675"], "is_dir": false }, { "id": "8.4", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3408"], "is_dir": false }, { "id": "8.5", "sev": "R", "full_sev": "MISRA-R", "warnings": ["1513", "3221", "3222", "3447", "3451"], "is_dir": false }, { "id": "8.6", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0630", "1509", "3406"], "is_dir": false }, { "id": "8.8", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3224"], "is_dir": false }, { "id": "8.10", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3240", "3243"], "is_dir": false }, { "id": "8.12", "sev": "R", "full_sev": "MISRA-R", "warnings": ["724"], "is_dir": false }, { "id": "8.14", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0669", "1057", "5137"], "is_dir": false }, { "id": "9.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0693", "0694"], "is_dir": false }, { "id": "9.3", "sev": "R", "full_sev": "MISRA-R", "warnings": ["686"], "is_dir": false }, { "id": "9.4", "sev": "R", "full_sev": "MISRA-R", "warnings": ["1397", "1398", "1399"], "is_dir": false }, { "id": "9.5", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3676"], "is_dir": false }, { "id": "10.1", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3101", "3102", "4500", "4501", "4502", "4503", "4504", "4505", "4507", "4510", "4511", "4512", "4513", "4514", "4518", "4519", "4521", "4522", "4523", "4524", "4527", "4528", "4529", "4532", "4533", "4534", "4538", "4539", "4542", "4543", "4548", "4549", "4558", "4559", "4568", "4569"], "is_dir": false }, { "id": "10.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["1810", "1811", "1812", "1813"], "is_dir": false }, { "id": "10.3", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0570", "0572", "1257", "1264", "1265", "1266", "1291", "1292", "1293", "1294", "1295", "1296", "1297", "1298", "1299", "2850", "2851", "2852", "2890", "2891", "2892", "2900", "2901", "2902", "4401", "4402", "4403", "4404", "4405", "4410", "4412", "4413", "4414", "4415", "4420", "4421", "4422", "4423", "4424", "4425", "4430", "4431", "4432", "4434", "4435", "4437", "4440", "4441", "4442", "4443", "4445", "4446", "4447", "4450", "4451", "4452", "4453", "4454", "4460", "4461", "4462", "4463", "4464", "4465"], "is_dir": false }, { "id": "10.4", "sev": "R", "full_sev": "MISRA-R", "warnings": ["1800", "1802", "1803", "1804", "1820", "1821", "1822", "1823", "1824", "1830", "1831", "1832", "1833", "1834", "1840", "1841", "1842", "1843", "1844", "1850", "1851", "1852", "1853", "1854", "1860", "1861", "1862", "1863", "1864", "1880", "1881", "1882"], "is_dir": false }, { "id": "10.6", "sev": "R", "full_sev": "MISRA-R", "warnings": ["4490", "4491", "4492", "4499"], "is_dir": false }, { "id": "10.7", "sev": "R", "full_sev": "MISRA-R", "warnings": ["1890", "1891", "1892", "1893", "1894", "1895"], "is_dir": false }, { "id": "10.8", "sev": "R", "full_sev": "MISRA-R", "warnings": ["4390", "4391", "4392", "4393", "4394", "4395", "4398", "4399"], "is_dir": false }, { "id": "11.1", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0302", "0305", "0307", "0313"], "is_dir": false }, { "id": "11.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["308"], "is_dir": false }, { "id": "11.3", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0310", "3305"], "is_dir": false }, { "id": "11.6", "sev": "R", "full_sev": "MISRA-R", "warnings": ["306"], "is_dir": false }, { "id": "11.7", "sev": "R", "full_sev": "MISRA-R", "warnings": ["301"], "is_dir": false }, { "id": "11.8", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0311", "0312"], "is_dir": false }, { "id": "11.9", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3003", "3004"], "is_dir": false }, { "id": "12.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0499", "2790"], "is_dir": false }, { "id": "13.1", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3421"], "is_dir": false }, { "id": "13.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0400", "0401", "0402", "0403"], "is_dir": false }, { "id": "13.5", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3415"], "is_dir": false }, { "id": "14.1", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3340", "3342"], "is_dir": false }, { "id": "14.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2461", "2462", "2463", "2464", "2467", "2469", "2471", "2472"], "is_dir": false }, { "id": "14.3", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2990", "2991", "2992", "2993", "2994"], "is_dir": false }, { "id": "14.4", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3344"], "is_dir": false }, { "id": "15.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3310"], "is_dir": false }, { "id": "15.3", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3311", "3327"], "is_dir": false }, { "id": "15.6", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2212", "2214", "3402"], "is_dir": false }, { "id": "15.7", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2004"], "is_dir": false }, { "id": "16.1", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2008", "3234"], "is_dir": false }, { "id": "16.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2019"], "is_dir": false }, { "id": "16.3", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2003", "2020"], "is_dir": false }, { "id": "16.4", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2002"], "is_dir": false }, { "id": "16.5", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2009"], "is_dir": false }, { "id": "16.6", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3315"], "is_dir": false }, { "id": "16.7", "sev": "R", "full_sev": "MISRA-R", "warnings": ["735"], "is_dir": false }, { "id": "17.1", "sev": "R", "full_sev": "MISRA-R", "warnings": ["1337", "5130"], "is_dir": false }, { "id": "17.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["1520", "3670"], "is_dir": false }, { "id": "17.7", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3200"], "is_dir": false }, { "id": "18.1", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2930", "2931", "2932"], "is_dir": false }, { "id": "18.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2761", "2762"], "is_dir": false }, { "id": "18.3", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2771", "2772"], "is_dir": false }, { "id": "18.6", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3217", "3225", "3230", "4140"], "is_dir": false }, { "id": "18.7", "sev": "R", "full_sev": "MISRA-R", "warnings": ["1060"], "is_dir": false }, { "id": "18.8", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0945", "1051", "1052"], "is_dir": false }, { "id": "20.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0813", "0814", "0831"], "is_dir": false }, { "id": "20.3", "sev": "R", "full_sev": "MISRA-R", "warnings": ["809"], "is_dir": false }, { "id": "20.4", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3439"], "is_dir": false }, { "id": "20.6", "sev": "R", "full_sev": "MISRA-R", "warnings": ["853"], "is_dir": false }, { "id": "20.7", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3410"], "is_dir": false }, { "id": "20.8", "sev": "R", "full_sev": "MISRA-R", "warnings": ["894"], "is_dir": false }, { "id": "20.9", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3332"], "is_dir": false }, { "id": "20.11", "sev": "R", "full_sev": "MISRA-R", "warnings": ["892"], "is_dir": false }, { "id": "20.12", "sev": "R", "full_sev": "MISRA-R", "warnings": ["893"], "is_dir": false }, { "id": "20.13", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3115"], "is_dir": false }, { "id": "20.14", "sev": "R", "full_sev": "MISRA-R", "warnings": ["3317", "3318"], "is_dir": false }, { "id": "21.1", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0836", "0848", "0854", "4600", "4601"], "is_dir": false }, { "id": "21.2", "sev": "R", "full_sev": "MISRA-R", "warnings": ["0602", "4602", "4603", "4604", "4605", "4606", "4607", "4608"], "is_dir": false }, { "id": "21.3", "sev": "R", "full_sev": "MISRA-R", "warnings": ["5118"], "is_dir": false }, { "id": "21.4", "sev": "R", "full_sev": "MISRA-R", "warnings": ["5132"], "is_dir": false }, { "id": "21.5", "sev": "R", "full_sev": "MISRA-R", "warnings": ["5123"], "is_dir": false }, { "id": "21.6", "sev": "R", "full_sev": "MISRA-R", "warnings": ["5124"], "is_dir": false }, { "id": "21.7", "sev": "R", "full_sev": "MISRA-R", "warnings": ["5125"], "is_dir": false }, { "id": "21.8", "sev": "R", "full_sev": "MISRA-R", "warnings": ["5126", "5128"], "is_dir": false }, { "id": "21.9", "sev": "R", "full_sev": "MISRA-R", "warnings": ["5135"], "is_dir": false }, { "id": "21.10", "sev": "R", "full_sev": "MISRA-R", "warnings": ["5127"], "is_dir": false }, { "id": "21.11", "sev": "R", "full_sev": "MISRA-R", "warnings": ["5131"], "is_dir": false }, { "id": "21.14", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2785", "2786"], "is_dir": false }, { "id": "21.15", "sev": "R", "full_sev": "MISRA-R", "warnings": ["1487", "1495", "1496"], "is_dir": false }, { "id": "21.16", "sev": "R", "full_sev": "MISRA-R", "warnings": ["1488", "1489", "1490", "1491", "1497"], "is_dir": false }, { "id": "22.7", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2676"], "is_dir": false }, { "id": "22.8", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2500"], "is_dir": false }, { "id": "22.9", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2501"], "is_dir": false }, { "id": "22.10", "sev": "R", "full_sev": "MISRA-R", "warnings": ["2503"], "is_dir": false }, { "id": "1.2", "sev": "A", "full_sev": "MISRA-A", "warnings": ["0240", "0241", "0246", "0551", "0601", "0633", "0635", "0660", "0662", "0830", "0831", "0899", "1001", "1002", "1003", "1006", "1008", "1012", "1014", "1015", "1019", "1020", "1021", "1022", "1026", "1028", "1029", "1034", "1035", "1036", "1037", "1038", "1041", "1042", "1043", "1044", "1045", "1046", "3664"], "is_dir": false }, { "id": "2.3", "sev": "A", "full_sev": "MISRA-A", "warnings": ["3205"], "is_dir": false }, { "id": "2.4", "sev": "A", "full_sev": "MISRA-A", "warnings": ["3213"], "is_dir": false }, { "id": "2.5", "sev": "A", "full_sev": "MISRA-A", "warnings": ["3214"], "is_dir": false }, { "id": "2.6", "sev": "A", "full_sev": "MISRA-A", "warnings": ["3202"], "is_dir": false }, { "id": "2.7", "sev": "A", "full_sev": "MISRA-A", "warnings": ["3206"], "is_dir": false }, { "id": "5.9", "sev": "A", "full_sev": "MISRA-A", "warnings": ["1525", "1527", "1528"], "is_dir": false }, { "id": "8.7", "sev": "A", "full_sev": "MISRA-A", "warnings": ["1504", "1505"], "is_dir": false }, { "id": "8.9", "sev": "A", "full_sev": "MISRA-A", "warnings": ["1514", "3218"], "is_dir": false }, { "id": "8.11", "sev": "A", "full_sev": "MISRA-A", "warnings": ["3684"], "is_dir": false }, { "id": "8.13", "sev": "A", "full_sev": "MISRA-A", "warnings": ["3673"], "is_dir": false }, { "id": "10.5", "sev": "A", "full_sev": "MISRA-A", "warnings": ["4301", "4302", "4303", "4304", "4305", "4310", "4312", "4315", "4320", "4322", "4330", "4332", "4340", "4342", "4350", "4351", "4352"], "is_dir": false }, { "id": "11.4", "sev": "A", "full_sev": "MISRA-A", "warnings": ["0303", "0306", "0360", "0361", "0362"], "is_dir": false }, { "id": "11.5", "sev": "A", "full_sev": "MISRA-A", "warnings": ["0316", "0317"], "is_dir": false }, { "id": "12.1", "sev": "A", "full_sev": "MISRA-A", "warnings": ["3389", "3391", "3392", "3394", "3395", "3396", "3397"], "is_dir": false }, { "id": "12.3", "sev": "A", "full_sev": "MISRA-A", "warnings": ["3417", "3418"], "is_dir": false }, { "id": "12.4", "sev": "A", "full_sev": "MISRA-A", "warnings": ["2910"], "is_dir": false }, { "id": "13.3", "sev": "A", "full_sev": "MISRA-A", "warnings": ["3440"], "is_dir": false }, { "id": "13.4", "sev": "A", "full_sev": "MISRA-A", "warnings": ["3226", "3326"], "is_dir": false }, { "id": "15.1", "sev": "A", "full_sev": "MISRA-A", "warnings": ["2001"], "is_dir": false }, { "id": "15.4", "sev": "A", "full_sev": "MISRA-A", "warnings": ["771"], "is_dir": false }, { "id": "15.5", "sev": "A", "full_sev": "MISRA-A", "warnings": ["2889"], "is_dir": false }, { "id": "17.5", "sev": "A", "full_sev": "MISRA-A", "warnings": ["2781", "2782", "2783", "2784"], "is_dir": false }, { "id": "17.8", "sev": "A", "full_sev": "MISRA-A", "warnings": ["1338", "1339", "1340"], "is_dir": false }, { "id": "18.4", "sev": "A", "full_sev": "MISRA-A", "warnings": ["488"], "is_dir": false }, { "id": "18.5", "sev": "A", "full_sev": "MISRA-A", "warnings": ["3260", "3261", "3262", "3263"], "is_dir": false }, { "id": "19.2", "sev": "A", "full_sev": "MISRA-A", "warnings": ["0750", "0759"], "is_dir": false }, { "id": "20.1", "sev": "A", "full_sev": "MISRA-A", "warnings": ["5087"], "is_dir": false }, { "id": "20.5", "sev": "A", "full_sev": "MISRA-A", "warnings": ["841"], "is_dir": false }, { "id": "20.10", "sev": "A", "full_sev": "MISRA-A", "warnings": ["0341", "0342"], "is_dir": false }, { "id": "21.12", "sev": "A", "full_sev": "MISRA-A", "warnings": ["5136"], "is_dir": false }];

/* ============================================================
   INDEX PAGE
   ============================================================ */
function initIndexPage() {
  const excelInput = document.getElementById("excel-input");
  const cInput = document.getElementById("c-input");
  const excelZone = document.getElementById("excel-zone");
  const cZone = document.getElementById("c-zone");
  const excelList = document.getElementById("excel-list");
  const cList = document.getElementById("c-list");
  const uploadError = document.getElementById("upload-error");
  const fileMappingSec = document.getElementById("file-mapping-section");
  const fileMapList = document.getElementById("file-map-list");
  const fileSummary = document.getElementById("file-summary");
  const runAllBtn = document.getElementById("run-all-btn");
  const clearCatBtn = document.getElementById("clear-cat-btn");

  let excelFile = null;
  let cFilesList = [];
  let uploadSessionId = null;   // set after /api/save_uploads succeeds
  let parsedExcelData = [];   // [{fileName, ruleId, message, warningNumbers, functionName}]
  let fileMappings = {};   // { fileName: [warnings] }
  let currentRunId = null;

  /* Track which file indices have already been run — must be declared BEFORE
     _restoreRuns so the IIFE can call _ranFiles.add() inside its try block.
     (const is not hoisted into IIFEs, so placing this after caused a silent
     ReferenceError that made Bug 3 "already-run files lose their done state".) */
  const _ranFiles = new Set();

  // ── Restore previously completed run cards (Back navigation) ──

  /* FIX 1: Helper – builds warning table HTML from restored parsedExcelData */
  function _buildRestoredWarningBody(fname, mappings) {
    var warnings = (mappings && mappings[fname]) || [];
    if (!warnings.length) return '<div class="fmap-no-warn">No warnings from the report reference this file.</div>';
    var rows = warnings.map(function (w) {
      return '<tr>'
        + '<td><span class="fmap-rule-pill">' + escHtml(w.ruleId || '') + '</span></td>'
        + '<td class="fmap-func">' + escHtml(w.funcName || '') + '</td>'
        + '<td class="fmap-msg">' + escHtml(w.message || '') + '</td>'
        + '<td class="fmap-warnno">' + escHtml((w.warnNo || '').length > 40 ? (w.warnNo || '').slice(0, 40) + '…' : (w.warnNo || '')) + '</td>'
        + '</tr>';
    }).join('');
    return '<table class="fmap-warn-table"><thead><tr><th>Rule</th><th>Function</th><th>Message</th><th>Warning Nos.</th></tr></thead><tbody>' + rows + '</tbody></table>';
  }

  (function _restoreRuns() {
    /* Always init side panel first — openSidePanel() needs it even if we return early */
    _initSidePanel();
    try {
      /* Restore upload session so pending files can be run without re-uploading */
      var _usess = JSON.parse(sessionStorage.getItem("misra_upload_session") || "null");
      if (_usess && _usess.id) {
        uploadSessionId = _usess.id;
        /* Rebuild cFilesList as lightweight objects (name only) so runSingleFile works */
        if (_usess.allFiles && _usess.allFiles.length) {
          cFilesList = _usess.allFiles.map(function (n) { return { name: n, _serverOnly: true }; });
        }
      }
    } catch (e) { console.error("restore upload session error:", e); }
    try {
      /* Restore file mapping section (shows ran vs pending files) */
      var _fstate = JSON.parse(sessionStorage.getItem("misra_file_state") || "null");
      if (_fstate && _fstate.allFiles && _fstate.allFiles.length) {
        var _ranSet = new Set(_fstate.ranFiles || []);
        var _fml = document.getElementById("file-map-list");
        var _fms = document.getElementById("file-mapping-section");
        var _fsm = document.getElementById("file-summary");
        if (_fml && _fms) {
          _fml.innerHTML = "";
          /* FIX 1d: rebuild warning mappings from persisted parsedExcelData */
          var _restoredMappings = {};
          (_fstate.parsedExcelData || []).forEach(function (row) {
            var fn = row.fileName || row.filename || '';
            if (!_restoredMappings[fn]) _restoredMappings[fn] = [];
            _restoredMappings[fn].push(row);
          });
          _fstate.allFiles.forEach(function (fname, idx) {
            var isDone = _ranSet.has(fname);
            var card = document.createElement("div");
            card.className = "fmap-card" + (isDone ? " fmap-ran" : "");
            card.id = "fmap-" + idx;
            var actionHtml;
            if (isDone) {
              actionHtml = '<button class="btn btn-ghost btn-sm fmap-run-btn fmap-done-btn" disabled>\u2713 Done</button>';
            } else if (uploadSessionId) {
              actionHtml = '<button class="btn btn-ghost btn-sm fmap-run-btn" onclick="runSingleFile(event,' + idx + ')">'
                + '<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>'
                + ' Run This File</button>';
            } else {
              actionHtml = '<span class="fmap-badge" style="font-size:11px;color:var(--text-muted)">Re-upload files to run</span>';
            }
            /* Always include chevron + body for ALL cards (done or not) so the user
               can expand a completed card to see its warnings. Bug fix: previously
               done cards had no chevron rendered here, making the accordion unusable
               after back-navigation even though the card was supposed to be interactive. */
            var chevronHtml = '<svg class="fmap-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>';
            var headerOnclick = ' onclick="toggleFmapCard(' + idx + ')"';
            card.innerHTML = '<div class="fmap-card-header"' + headerOnclick + '>'
              + '<div class="fmap-file-info">'
              + '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>'
              + '<span class="fmap-filename">' + escHtml(fname) + '</span>'
              + '</div>'
              + '<div class="fmap-actions">' + actionHtml + chevronHtml + '</div></div>'
              + '<div class="fmap-card-body hidden" id="fmap-body-' + idx + '">' + _buildRestoredWarningBody(fname, _restoredMappings) + '</div>';
            _fml.appendChild(card);
          });
          /* Bug 3 fix: repopulate _ranFiles so already-run files stay marked done */
          _fstate.allFiles.forEach(function (fname, idx) {
            if (_ranSet.has(fname)) _ranFiles.add(idx);
          });
          /* BUG 1 FIX: Restore parsedExcelData from saved state so the live variable
             is never empty when the next run completes and re-saves misra_file_state.
             Without this, running logger.c after control.c (on Back navigation) would
             overwrite misra_file_state with parsedExcelData=[] — wiping all warning
             mappings and showing "No warnings" for already-done files. */
          if (_fstate.parsedExcelData && _fstate.parsedExcelData.length) {
            parsedExcelData = _fstate.parsedExcelData;
          }
          /* Remove the "Run This File" onclick from done-card headers.
             We keep toggleFmapCard so users can expand to view warnings,
             but runSingleFile must NOT re-trigger on disabled done cards. */
          _fstate.allFiles.forEach(function (fname, idx) {
            if (!_ranSet.has(fname)) return;
            var fcard = document.getElementById("fmap-" + idx);
            if (!fcard) return;
            fcard.classList.add("fmap-ran");
          });
          var totalFiles = _fstate.allFiles.length;
          var ranCount = _fstate.ranFiles ? _fstate.ranFiles.length : 0;
          if (_fsm) _fsm.textContent = totalFiles + " file" + (totalFiles !== 1 ? "s" : "") + " \u00b7 " + ranCount + " analysed";
          _fms.classList.remove("hidden");
        }
      }
    } catch (e) { console.error("restore file state error:", e); }
    try {
      var saved = JSON.parse(sessionStorage.getItem("misra_completed_runs") || "[]");
      if (!saved.length) return;
      var pp = document.getElementById("progress-panel"); if (!pp) return;
      pp.classList.add("visible");
      // Set pipeline status to green "Ready" (not red "Analysing")
      var _st = document.getElementById("pipeline-status-tag");
      var _sd = document.getElementById("pipeline-status-dot");
      var _sl = document.getElementById("pipeline-status-label");
      if (_st) { _st.style.background = "rgba(16,185,129,.08)"; _st.style.color = "#065f46"; _st.style.borderColor = "rgba(16,185,129,.25)"; }
      if (_sd) { _sd.style.background = "#10b981"; _sd.style.animation = "none"; }
      if (_sl) _sl.textContent = "Report Ready";
      // Mark all pipeline phase steps as done
      ["ph-6a", "ph-6b", "ph-7", "ph-8", "ph-done"].forEach(function (id) {
        var el = document.getElementById(id); if (!el) return;
        el.classList.remove("active", "error"); el.classList.add("done");
        var b = el.querySelector(".phase-badge"); if (b) b.textContent = "\u2713";
        var d = el.querySelector(".phase-detail"); if (d) d.textContent = "Complete";
      });
      // Create/find records wrapper
      var rw = document.getElementById("per-record-wrap");
      if (!rw) {
        rw = document.createElement("div"); rw.id = "per-record-wrap"; rw.className = "per-record-wrap";
        var anc = pp.querySelector(".progress-section") || pp; pp.insertBefore(rw, anc);
      }
      var ce = document.getElementById("pr-counter");
      if (!ce) {
        ce = document.createElement("div"); ce.id = "pr-counter"; pp.insertBefore(ce, rw);
      }
      var RP = [{ ph: "6a", lb: "Read" }, { ph: "6b", lb: "Rules" }, { ph: "7", lb: "Fix" }, { ph: "8", lb: "Check" }, { ph: "done", lb: "Done" }];
      var tot = 0;
      var _restoreLastFile = null;  /* FIX 3: track last file for group headers */
      saved.forEach(function (run) {
        var rid = run.runId;
        var widFiles = run.widFiles || {};
        (run.wids || []).forEach(function (wid) {
          if (document.getElementById("prcard-" + wid)) return;

          /* FIX 3: Insert file-group header before this card if file changed */
          var cardFile = widFiles[wid] || null;
          if (cardFile && cardFile !== _restoreLastFile) {
            _restoreLastFile = cardFile;
            var existHdr = document.getElementById("pr-file-hdr-" + cardFile.replace(/[^a-zA-Z0-9]/g, '_'));
            if (!existHdr) {
              var hdr = document.createElement('div');
              hdr.className = 'pr-file-group-hdr pr-file-group-hdr-collapsible';
              hdr.id = 'pr-file-hdr-' + cardFile.replace(/[^a-zA-Z0-9]/g, '_');
              hdr.setAttribute('data-file-group', cardFile);
              hdr.setAttribute('data-collapsed', 'false');
              hdr.onclick = function () { window._toggleFileGroup(cardFile); };
              /* Count wids in this group */
              var _grpCount = (run.widFiles ? Object.values(run.widFiles).filter(function (f) { return f === cardFile; }).length : 0)
                || (run.wids ? run.wids.filter(function (w) { return widFiles[w] === cardFile; }).length : 0);
              hdr.innerHTML = '<div class="pr-fhdr-left">'
                + '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>'
                + '<span class="pr-fhdr-name">' + escHtml(cardFile) + '</span>'
                + (_grpCount ? '<span class="pr-fhdr-badge">' + _grpCount + ' warning' + (_grpCount !== 1 ? 's' : '') + '</span>' : '')
                + '</div>'
                + '<div class="pr-fhdr-right">'
                + '<span class="pr-fhdr-status">&#10003; Done</span>'
                + '<svg class="pr-file-grp-chevron" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>'
                + '</div>';
              rw.appendChild(hdr);
            }
          }
          // Build step rings (all green/done)
          var st = '<div class="pr-steps-bar">';
          RP.forEach(function (p, i) {
            st += '<div class="pr-step-item pr-step-done" id="prstep-' + wid + '-' + p.ph + '">'
              + '<div class="pr-step-node"><span class="pr-step-check">&#10003;</span><span class="pr-step-dot"></span></div>'
              + '<span class="pr-step-lbl">' + p.lb + '</span></div>';
            if (i < RP.length - 1)
              st += '<div class="pr-step-line pr-step-line-done" id="prline-' + wid + '-' + i + '"></div>';
          });
          st += '</div>';
          /* BUG B FIX: restored cards also need the pr-bar (already 100% done) */
          st += '<div class="pr-bar"><div class="pr-bar-fill pr-bar-fill-done" id="prbar-' + wid + '" style="width:100%"></div></div>';
          var card = document.createElement("div");
          card.className = "pr-card pr-card-done"; card.id = "prcard-" + wid;
          if (cardFile) card.setAttribute('data-file-group', cardFile);
          card.innerHTML = '<div class="pr-header">'
            + '<span class="pr-wid">' + escHtml(wid) + '</span>'
            + '<span class="pr-status-badge pr-done">Complete</span>'
            + '<button class="pr-view-btn" onclick="openSidePanel(\u0027' + escHtml(wid) + '\u0027,\u0027' + escHtml(rid) + '\u0027)">View Result &#8594;</button>'
            + '</div>' + st;
          rw.appendChild(card); tot++;
        });
      });
      if (tot > 0) {
        var lr = saved[saved.length - 1];
        /* BUG 2C FIX: Show TOTAL across all saved runs, not just last run's total */
        var _grandTotal = saved.reduce(function (acc, r) { return acc + (r.total || 0); }, 0);
        ce.textContent = "All " + (_grandTotal || tot) + " records complete";
        ce.className = "pr-counter pr-counter-done";
        currentRunId = lr.runId;
        /* Fix Bug 4: update status line so it doesn't show "Starting up…" */
        var _sl2 = document.getElementById("status-line");
        if (_sl2) _sl2.textContent = "All done! Click any record to view its result.";
      }
    } catch (e) { console.error("restore error:", e); }

    /* FIX 4: Restore commit state so side panel shows ✓ Committed (not prompt again)
       when user navigates Back after having committed a fix in a previous visit. */
    try {
      var _storedCommits = JSON.parse(sessionStorage.getItem("misra_commits") || "{}");
      if (Object.keys(_storedCommits).length) {
        window._commitResults = window._commitResults || {};
        Object.keys(_storedCommits).forEach(function (wid) {
          var m = _storedCommits[wid];
          if (!window._commitResults[wid]) {
            /* Mark as committed in memory so openSidePanel restores correct state.
               patchedCode is fetched from server by _restoreCommittedPatches on Results page;
               here we only need the metadata flags for the side panel commit button. */
            window._commitResults[wid] = {
              afterCode: "",          // will be filled lazily if user opens side panel
              runId: m.runId || "",
              patchedCode: "",        // lazy — fetched from server on side panel open
              patchLineStart: m.patchLineStart || 0,
              patchLineCount: m.patchLineCount || 0,
              originalFile: m.originalFile || "",
              downloadUrl: m.downloadUrl || "",
              filename: m.filename || "patched.c",
              isFullFile: m.isFullFile || false,
              wasUserEdited: m.wasUserEdited || false,
              _needsServerLoad: true  // flag: patchedCode not yet loaded
            };
          }
        });
      }
      /* Also restore noChange selections */
      var _storedNoChange = JSON.parse(sessionStorage.getItem("misra_no_change") || "{}");
      if (Object.keys(_storedNoChange).length) {
        window._noChangeResults = window._noChangeResults || {};
        Object.keys(_storedNoChange).forEach(function (wid) {
          window._noChangeResults[wid] = true;
        });
      }
    } catch (e) { console.error("restore commit state error:", e); }
  })();

  /* ── Drop zones ── */
  [excelZone, cZone].forEach(zone => {
    zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("drag-over"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", e => {
      e.preventDefault(); zone.classList.remove("drag-over");
      const files = [...e.dataTransfer.files];
      zone === excelZone ? handleExcel(files[0]) : handleCFiles(files);
    });
    /* Make entire zone clickable → trigger file picker (not folder picker) */
    zone.addEventListener("click", function (e) {
      /* Ignore clicks on the pick buttons, folder input, or any input element */
      if (e.target.closest(".c-pick-btn")) return;
      if (e.target.closest("input")) return;
      if (zone === excelZone) {
        excelInput.click();
      } else {
        /* Default click on zone body opens file picker (not folder) */
        document.getElementById("c-input").click();
      }
    });
  });
  excelInput.addEventListener("change", () => handleExcel(excelInput.files[0]));

  /* File / Folder picker buttons for C source zone */
  const cPickFiles = document.getElementById("c-pick-files-btn");
  const cPickFolder = document.getElementById("c-folder-input");
  const cFolderBtn = document.getElementById("c-pick-folder-btn");
  const cFolderInput = document.getElementById("c-folder-input");
  if (cPickFiles) cPickFiles.addEventListener("click", e => { e.stopPropagation(); cInput.click(); });
  if (cFolderBtn) cFolderBtn.addEventListener("click", function (e) {
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    if (cFolderInput) { cFolderInput.value = ""; cFolderInput.click(); }
  });
  cInput.addEventListener("change", () => { if (cInput.files.length) handleCFiles([...cInput.files]); });
  if (cFolderInput) cFolderInput.addEventListener("change", () => {
    const valid = [...cFolderInput.files].filter(f => /\.(c|h)$/i.test(f.name));
    if (valid.length) handleCFiles(valid);
    else showError("No .c or .h files found in the selected folder.");
  });

  function handleExcel(file) {
    if (!file) return;
    var _en = file.name.toLowerCase(); if (!_en.endsWith(".xlsx") && !_en.endsWith(".xls")) { showError("Warning report must be .xlsx or .xls"); return; }
    excelFile = file;
    excelList.innerHTML = chipHTML(file.name);
    excelZone.classList.add("has-file");
    parseExcelClientSide(file).then(() => tryBuildMapping());
  }

  function handleCFiles(files) {
    const valid = files.filter(f => /\.(c|h)$/i.test(f.name));
    if (!valid.length) { showError("No .c or .h files found"); return; }
    cFilesList = valid;
    cList.innerHTML = valid.map(f => chipHTML(f.name)).join("");
    cZone.classList.add("has-file");
    tryBuildMapping();
  }

  function chipHTML(name) {
    return `<div class="file-chip"><span class="dot"></span>${escHtml(name)}</div>`;
  }

  /* ── Parse Excel client-side using SheetJS ── */
  async function parseExcelClientSide(file) {
    return new Promise(resolve => {
      const fr = new FileReader();
      fr.onload = function (e) {
        try {
          /* SheetJS loaded via CDN in index.html */
          const XLSX = window.XLSX;
          if (!XLSX) { parsedExcelData = []; resolve(); return; }

          const data = new Uint8Array(e.target.result);
          const wb = XLSX.read(data, { type: "array" });
          const ws = wb.Sheets[wb.SheetNames[0]];
          const rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: "" });

          if (rows.length < 2) { parsedExcelData = []; resolve(); return; }

          /* Detect column indices from header row */
          const header = rows[0].map(h => String(h).trim().toLowerCase());
          const col = {
            warnNo: header.findIndex(h => h.includes("warning")),
            category: header.findIndex(h => h.includes("category")),
            ruleId: header.findIndex(h => h.includes("rule")),
            message: header.findIndex(h => h.includes("message") || h.includes("description")),
            fileName: header.findIndex(h => h.includes("file")),
            funcName: header.findIndex(h => h.includes("function"))
          };

          parsedExcelData = [];
          for (let i = 1; i < rows.length; i++) {
            const r = rows[i];
            if (!r || r.every(c => !c)) continue;   /* skip blank rows */
            const fn = col.fileName >= 0 ? String(r[col.fileName] || "").trim() : "";
            if (!fn) continue;
            parsedExcelData.push({
              fileName: fn,
              ruleId: col.ruleId >= 0 ? String(r[col.ruleId] || "").trim() : "",
              message: col.message >= 0 ? String(r[col.message] || "").trim() : "",
              warnNo: col.warnNo >= 0 ? String(r[col.warnNo] || "").trim() : "",
              funcName: col.funcName >= 0 ? String(r[col.funcName] || "").trim() : "",
              rowIndex: i
            });
          }
          resolve();
        } catch (e) {
          console.warn("Excel parse failed:", e);
          parsedExcelData = [];
          resolve();
        }
      };
      fr.onerror = resolve;
      fr.readAsArrayBuffer(file);   /* SheetJS needs ArrayBuffer */
    });
  }

  function tryBuildMapping() {
    if (!excelFile || !cFilesList.length) return;
    buildFileMappingUI();
    _saveUploadsToServer();
  }

  async function _saveUploadsToServer() {
    uploadSessionId = null;  // reset while saving
    try {
      const fd = new FormData();
      fd.append("warning_report", excelFile);
      cFilesList.forEach(f => fd.append("source_files", f));
      const resp = await fetch("/api/save_uploads", { method: "POST", body: fd });
      const data = await resp.json();
      if (resp.ok && data.upload_session_id) {
        uploadSessionId = data.upload_session_id;
        /* Persist so Back navigation can reuse the session */
        try {
          sessionStorage.setItem("misra_upload_session", JSON.stringify({
            id: uploadSessionId,
            allFiles: data.c_files,
            excelName: data.excel_filename
          }));
        } catch (e) { }
      } else {
        console.warn("save_uploads failed:", data.error);
      }
    } catch (e) {
      console.warn("save_uploads error:", e.message);
    }
  }

  function buildFileMappingUI() {
    fileMappings = {};

    /* Group parsed excel rows by file name */
    parsedExcelData.forEach(row => {
      const fn = row.fileName;
      if (!fileMappings[fn]) fileMappings[fn] = [];
      fileMappings[fn].push(row);
    });

    /* Also ensure every uploaded .c file gets an entry (even if no warnings mapped) */
    cFilesList.forEach(f => {
      if (!fileMappings[f.name]) fileMappings[f.name] = [];
    });

    fileMappingSec.classList.remove("hidden");
    renderFileMappingList();

    const totalWarningsMapped = parsedExcelData.length;
    const totalFiles = cFilesList.length;
    fileSummary.textContent =
      `${totalFiles} file${totalFiles !== 1 ? "s" : ""} · ${totalWarningsMapped} warning${totalWarningsMapped !== 1 ? "s" : ""} mapped`;
  }

  function renderFileMappingList() {
    fileMapList.innerHTML = "";

    cFilesList.forEach((f, idx) => {
      const fname = f.name;
      const warnings = fileMappings[fname] || [];
      const wCount = warnings.length;
      const badge = wCount > 0
        ? `<span class="fmap-badge fmap-badge-warn">${wCount} warning${wCount !== 1 ? "s" : ""}</span>`
        : `<span class="fmap-badge">No warnings mapped</span>`;

      /* Build warning rows HTML */
      let warningRowsHtml = "";
      if (wCount > 0) {
        warningRowsHtml = `
          <table class="fmap-warn-table">
            <thead>
              <tr>
                <th>Rule</th>
                <th>Function</th>
                <th>Message</th>
                <th>Warning Nos.</th>
              </tr>
            </thead>
            <tbody>
              ${warnings.map(w => `
                <tr>
                  <td><span class="fmap-rule-pill">${escHtml(w.ruleId)}</span></td>
                  <td class="fmap-func">${escHtml(w.funcName)}</td>
                  <td class="fmap-msg">${escHtml(w.message)}</td>
                  <td class="fmap-warnno">${escHtml(w.warnNo.length > 40 ? w.warnNo.slice(0, 40) + "…" : w.warnNo)}</td>
                </tr>`).join("")}
            </tbody>
          </table>`;
      } else {
        warningRowsHtml = `<div class="fmap-no-warn">No warnings from the report reference this file.</div>`;
      }

      const card = document.createElement("div");
      card.className = "fmap-card";
      card.id = "fmap-" + idx;

      card.innerHTML = `
        <div class="fmap-card-header" onclick="toggleFmapCard(${idx})">
          <div class="fmap-file-info">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            <span class="fmap-filename">${escHtml(fname)}</span>
            ${badge}
          </div>
          <div class="fmap-actions">
            <button class="btn btn-ghost btn-sm fmap-run-btn" onclick="runSingleFile(event, ${idx})">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              Run This File
            </button>
            <svg class="fmap-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </div>
        </div>
        <div class="fmap-card-body hidden" id="fmap-body-${idx}">
          ${warningRowsHtml}
        </div>`;

      fileMapList.appendChild(card);
    });
  }

  window.toggleFmapCard = function (idx) {
    const body = document.getElementById("fmap-body-" + idx);
    const card = document.getElementById("fmap-" + idx);
    if (body) body.classList.toggle("hidden");
    if (card) card.classList.toggle("fmap-open");
  };

  window.runSingleFile = function (e, idx) {
    e.stopPropagation();
    if (_ranFiles.has(idx)) return;   // already ran — do not re-run
    const f = cFilesList[idx];
    if (!f) return;
    /* Disable this file's run button immediately */
    const btn = document.querySelector(`#fmap-${idx} .fmap-run-btn`);
    if (btn) { btn.disabled = true; btn.textContent = "Running…"; }
    startAnalysis([f], idx);
  };

  runAllBtn && runAllBtn.addEventListener("click", () => {
    const pending = cFilesList.filter((_, i) => !_ranFiles.has(i));
    if (!pending.length) { showError("All files have already been analysed."); return; }
    startAnalysis(pending, null, true);
  });

  async function startAnalysis(srcFiles, fileIdx, isRunAll) {
    showError("");
    const progressPanel = document.getElementById("progress-panel");
    const uploadCard = document.getElementById("upload-card");
    progressPanel.classList.add("visible");
    uploadCard.style.opacity = "0.4";
    uploadCard.style.pointerEvents = "none";
    // Remove any old back button from a previous run
    const oldBack = document.getElementById("back-to-upload-btn");
    if (oldBack) oldBack.remove();
    /* Remember which file was just started so we can mark it done later */
    window._currentFileIdx = (fileIdx !== null && fileIdx !== undefined) ? fileIdx : null;
    window._currentIsRunAll = !!isRunAll;

    const fd = new FormData();

    // Send rule config — selected rules + overrides as filter
    const ruleSelected = [..._ruleState.selected];
    const ruleOverrides = _ruleState.overrides;
    fd.append("rule_selected", JSON.stringify(ruleSelected));
    fd.append("rule_overrides", JSON.stringify(ruleOverrides));

    if (uploadSessionId) {
      /* Fast path — files already on server, just send session ID + target filenames */
      fd.append("upload_session_id", uploadSessionId);
      srcFiles.forEach(f => fd.append("run_filenames", f.name));
    } else {
      /* Fallback — upload files now (e.g. session expired or save_uploads failed) */
      fd.append("warning_report", excelFile);
      srcFiles.forEach(f => fd.append("source_files", f));
    }

    try {
      const resp = await fetch("/api/analyse", { method: "POST", body: fd });
      const data = await resp.json();
      if (!resp.ok) {
        // ── FIX 2: handle session expiry with a clear, actionable message ──
        var errMsg = data.error || "Server error";
        if (errMsg.toLowerCase().includes("session not found") || errMsg.toLowerCase().includes("upload session")) {
          /* Session expired (e.g. server restarted). Clear stale session so
             the user is prompted to re-upload rather than looping on 400s. */
          uploadSessionId = null;
          try { sessionStorage.removeItem("misra_upload_session"); } catch (e) { }
          showError("Your upload session has expired — please re-upload your Excel report and C files to run again.");
          /* Re-enable all pending Run buttons so the user can act */
          cFilesList.forEach(function (_, i) {
            if (!_ranFiles.has(i)) {
              var btn = document.querySelector("#fmap-" + i + " .fmap-run-btn");
              if (btn) { btn.disabled = false; btn.innerHTML = '<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run This File'; }
            }
          });
        } else {
          showError(errMsg);
        }
        resetUI();
        return;
      }
      currentRunId = data.run_id;
      // Show filter notification if rules were filtered
      if (data.warnings_filtered && data.filtered_count !== undefined) {
        const statusLn = document.getElementById("status-line");
        if (statusLn) statusLn.textContent =
          `Rule filter applied — ${data.filtered_count} warning${data.filtered_count === 1 ? "" : "s"} queued for analysis`;
      }
      listenProgress(data.job_id, data.run_id, srcFiles);
    } catch (err) {
      showError("Connection error: " + err.message);
      resetUI();
    }
  }

  function resetUI() {
    const progressPanel = document.getElementById("progress-panel");
    const uploadCard = document.getElementById("upload-card");
    progressPanel.classList.remove("visible");
    uploadCard.style.opacity = "1";
    uploadCard.style.pointerEvents = "auto";
  }

  /* ── Category checkbox change (multi-select: any/all of M/R/A) ── */
  document.querySelectorAll('input[name="misra_category"]').forEach(cb => {
    cb.addEventListener("change", function () {
      const anyChecked = document.querySelectorAll('input[name="misra_category"]:checked').length > 0;
      clearCatBtn && (anyChecked ? clearCatBtn.classList.remove("hidden") : clearCatBtn.classList.add("hidden"));
    });
  });

  window.clearCategorySelection = function () {
    document.querySelectorAll('input[name="misra_category"]').forEach(r => r.checked = false);
    clearCatBtn && clearCatBtn.classList.add("hidden");
    sessionStorage.removeItem("misra_filter");
  };

  function showError(msg) {
    const el = document.getElementById("upload-error");
    if (!el) return;
    if (msg) { el.textContent = msg; el.classList.remove("hidden"); setTimeout(() => el.classList.add("hidden"), 6000); }
    else el.classList.add("hidden");
  }

  /* ── SSE progress ── */
  function listenProgress(jobId, runId, runSrcFiles) {
    const statusLn = document.getElementById("status-line");
    const oldWrap = document.getElementById("stream-table-wrap");
    if (oldWrap) oldWrap.classList.add("hidden");
    const progSec = document.querySelector(".progress-section");
    if (progSec) progSec.style.display = "none";

    const progressPanel = document.getElementById("progress-panel");
    let recordsWrap = document.getElementById("per-record-wrap");
    if (!recordsWrap) {
      recordsWrap = document.createElement("div");
      recordsWrap.id = "per-record-wrap"; recordsWrap.className = "per-record-wrap";
      const anchor = progressPanel.querySelector(".progress-section") || progressPanel;
      progressPanel.insertBefore(recordsWrap, anchor);
    } else {
      /* Remove only incomplete/stale cards (those without pr-card-done) so their
         __RID__ placeholders can't cause "Record not found". Completed cards from
         previous runs are kept so the user can still view their results. */
      Array.from(recordsWrap.querySelectorAll(".pr-card:not(.pr-card-done)")).forEach(el => el.remove());
    }
    let counterEl = document.getElementById("pr-counter");
    if (!counterEl) {
      counterEl = document.createElement("div"); counterEl.id = "pr-counter"; counterEl.className = "pr-counter";
      counterEl.textContent = "Waiting for records\u2026";
      progressPanel.insertBefore(counterEl, recordsWrap);
    } else {
      /* Reset counter text for the new run */
      counterEl.textContent = "Waiting for records\u2026";
      counterEl.className = "pr-counter";
    }

    /* Reset the big pipeline bar (Reading file → Looking up rules → … → Report ready)
       back to "Waiting…" so it reflects the new run's progress, not the previous one's. */
    ["ph-6a", "ph-6b", "ph-7", "ph-8", "ph-done"].forEach(function (id) {
      const el = document.getElementById(id);
      if (!el) return;
      el.classList.remove("active", "done", "error");
      const badge = el.querySelector(".phase-badge");
      if (badge) badge.textContent = id === "ph-6a" ? "1" : id === "ph-6b" ? "2" : id === "ph-7" ? "3" : id === "ph-8" ? "4" : "5";
      const detail = el.querySelector(".phase-detail");
      if (detail) detail.textContent = "Waiting\u2026";
    });
    /* Reset pipeline status tag back to red "Analysing…" */
    const _resetTag = document.getElementById("pipeline-status-tag");
    const _resetDot = document.getElementById("pipeline-status-dot");
    const _resetLbl = document.getElementById("pipeline-status-label");
    if (_resetTag) { _resetTag.style.background = "rgba(192,57,43,.07)"; _resetTag.style.color = "var(--red,#c0392b)"; _resetTag.style.borderColor = "rgba(192,57,43,.2)"; }
    if (_resetDot) { _resetDot.style.background = "var(--red,#c0392b)"; _resetDot.style.animation = "pulse-dot 1.2s infinite"; }
    if (_resetLbl) _resetLbl.textContent = "Analysing\u2026";

    /* Side panel */
    _initSidePanel(); // panel created once at module level

    function _startElapsedTicker() { }
    function _stopElapsedTicker() { }
    // openSidePanel is defined at module level below
    _initSidePanel(); // ensure side panel DOM exists for this run

    /* Per-record tracking */
    const recordMeta = {}; let totalWarnings = 0, doneCount = 0;

    /* FEATURE 1: Map wid → filename so cards can be grouped under file headers */
    const _widFileMap = {};
    let _lastGroupFile = null;

    /* Build wid→file map using TWO sources:
       1. Primary: the actual file(s) being run right now (srcFiles) — most accurate
          because the orchestrator processes one file at a time.
       2. Fallback: parsedExcelData (Excel warning→file mapping).
       This prevents sensor.c warnings being grouped under uninit_read.c when both
       files share warning 2883. */
    (function _buildWidFileMap() {
      /* Source 1: if a single file is being run, ALL wids from this run belong to it.
         We store it as the "current run file" and assign it to every new wid seen. */
      if (runSrcFiles && runSrcFiles.length === 1) {
        window._currentRunFileName = runSrcFiles[0].name;
      } else {
        window._currentRunFileName = null;
        /* Source 2 fallback: build from parsedExcelData for multi-file runs */
        if (parsedExcelData && parsedExcelData.length) {
          parsedExcelData.forEach(function (row) {
            var fn = row.fileName || row.filename || '';
            var wno = String(row.warnNo || row.warning_id || '').trim();
            if (fn && wno) _widFileMap[wno] = fn;
          });
        }
      }
    })();

    function _insertFileGroupHeader(wid) {
      /* For single-file runs: all wids belong to _currentRunFileName */
      var fname = window._currentRunFileName || _widFileMap[wid] || null;
      /* Also try stripping suffix like _uninit_read to find base wid */
      if (!fname && !window._currentRunFileName) {
        var baseWid = wid.replace(/_[a-zA-Z0-9_]+$/, '');
        fname = _widFileMap[baseWid] || null;
      }
      if (!fname || fname === _lastGroupFile) return;
      _lastGroupFile = fname;
      var hdr = document.createElement('div');
      hdr.className = 'pr-file-group-hdr pr-file-group-hdr-collapsible';
      hdr.id = 'pr-file-hdr-' + fname.replace(/[^a-zA-Z0-9]/g, '_');
      hdr.setAttribute('data-file-group', fname);
      hdr.setAttribute('data-collapsed', 'false');
      hdr.onclick = function () { window._toggleFileGroup(fname); };
      hdr.innerHTML = '<div class="pr-fhdr-left">'
        + '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>'
        + '<span class="pr-fhdr-name">' + escHtml(fname) + '</span>'
        + '</div>'
        + '<div class="pr-fhdr-right">'
        + '<span class="pr-fhdr-status pr-fhdr-running">&#9679; Analysing</span>'
        + '<svg class="pr-file-grp-chevron" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>'
        + '</div>';
      recordsWrap.insertBefore(hdr, _runInsertPoint);
    }
    /* Track ONLY the wids introduced by this run (not recycled from previous runs).
       This prevents the sessionStorage save from bundling old wids under the new runId,
       which would cause "Record not found" when View Result is clicked on old cards. */
    const currentRunWids = new Set();

    /* NEW: anchor = first child of recordsWrap at the moment listenProgress() starts.
       All cards created for THIS run are inserted BEFORE this anchor so they
       always appear at the TOP of the list, above any old restored done cards.
       Without this, new cards were appended at the bottom and the user wouldn't
       see them without scrolling past the old completed run cards.
       MUST be `let` (not `const`) so the stash branch can update it when the
       anchor card itself gets moved to #pr-stash. */
    let _runInsertPoint = recordsWrap.firstChild || null;
    const RING_PHASES = [
      { ph: "6a", label: "Read", pct: 20 },
      { ph: "6b", label: "Rules", pct: 40 },
      { ph: "7", label: "Fix", pct: 60 },
      { ph: "8", label: "Check", pct: 80 },
      { ph: "done", label: "Done", pct: 100 },
    ];
    const RING_ORDER = RING_PHASES.map(r => r.ph);

    function _stepsHtml(wid) {
      let out = '<div class="pr-steps-bar">';
      RING_PHASES.forEach(({ ph, label }, i) => {
        out += `<div class="pr-step-item pr-step-pending" id="prstep-${escHtml(wid)}-${ph}">
          <div class="pr-step-node"><span class="pr-step-check">&#10003;</span><span class="pr-step-dot"></span></div>
          <span class="pr-step-lbl">${label}</span>
        </div>`;
        if (i < RING_PHASES.length - 1)
          out += `<div class="pr-step-line" id="prline-${escHtml(wid)}-${i}"></div>`;
      });
      out += '</div>';
      /* FIX 3+4: linear progress bar that advances with each phase */
      out += `<div class="pr-bar"><div class="pr-bar-fill" id="prbar-${escHtml(wid)}" style="width:0%"></div></div>`;
      return out;
    }

    function ensureRecord(wid) {
      if (recordMeta[wid]) return recordMeta[wid];

      /* If a card for this wid already exists in the DOM (e.g. restored from a
         previous run via _restoreRuns), we MUST reset it to a fresh "running" state.
         ─ We cannot simply reuse it as-is: the pr-card-done class causes setPhase()
           and markDone() to bail out early, so no progress would ever show.
         ─ We cannot leave the old HTML: prstep-/prline- IDs need fresh pending state.
         The old card is replaced in-place so its DOM position is preserved. */
      const existingCard = document.getElementById("prcard-" + wid);
      if (existingCard) {
        if (existingCard.classList.contains("pr-card-done")) {
          /* ROOT FIX: The old card is a completed card from a previous run.
             We must NOT leave it in the DOM while the new card runs — shared
             element IDs (prstep-*, prline-*, prbar-*, prstatus-*, prview-*)
             would cause document.getElementById() to return the OLD card's
             elements, making all progress updates invisible on the new card
             and "Record not found" when View Result is clicked.

             CRITICAL: Before stashing the old card, we MUST strip all
             conflicting IDs from it. Even in a display:none container,
             getElementById() still finds elements by ID — it returns the
             FIRST match in document order. If the stashed card keeps its
             IDs, every getElementById("prbar-{wid}") etc. will return the
             stashed card's (hidden) element, not the new card's element.
             This makes the progress bar invisible and causes __RID__ to
             never be replaced on the new card's View Result button. */
          var _stash = document.getElementById("pr-stash");
          if (!_stash) {
            _stash = document.createElement("div");
            _stash.id = "pr-stash";
            _stash.style.cssText = "display:none!important;position:absolute;left:-9999px";
            document.body.appendChild(_stash);
          }
          /* Strip ALL conflicting IDs from the old card BEFORE stashing it.
             This ensures getElementById() for the new card's IDs always
             returns the new card's elements, not the stashed card's. */
          var _conflictingIds = [
            "prstatus-" + wid, "prview-" + wid, "prbar-" + wid
          ];
          RING_PHASES.forEach(function (p, i) {
            _conflictingIds.push("prstep-" + wid + "-" + p.ph);
            if (i < RING_PHASES.length - 1) _conflictingIds.push("prline-" + wid + "-" + i);
          });
          _conflictingIds.forEach(function (id) {
            var el = existingCard.querySelector("#" + id);
            if (el) el.removeAttribute("id");
          });
          /* Give the old card a stash id so we can identify it later */
          existingCard.id = "prcard-stash-" + wid;

          /* SAFE INSERT: capture position BEFORE stashing the old card.
             We must record nextSibling while the old card is still in recordsWrap.
             After _stash.appendChild(existingCard) it is removed from recordsWrap. */
          const _stashNextSib = existingCard.nextSibling;
          if (_runInsertPoint === existingCard) {
            _runInsertPoint = _stashNextSib;
          }

          _stash.appendChild(existingCard);  // remove from live DOM
          /* Build fresh running card */
          const newCard = document.createElement("div");
          newCard.className = "pr-card stream-new";
          newCard.id = "prcard-" + wid;
          newCard.innerHTML = `
            <div class="pr-header">
              <span class="pr-wid">${escHtml(wid)}</span>
              <span class="pr-status-badge pr-running" id="prstatus-${escHtml(wid)}">Processing\u2026</span>
              <button class="pr-view-btn hidden" id="prview-${escHtml(wid)}"
                onclick="openSidePanel('${escHtml(wid)}','__RID__')">View Result &#8594;</button>
            </div>
            ${_stepsHtml(wid)}`;
          /* Insert at the top of the list (where the anchor was) */
          recordsWrap.insertBefore(newCard, _stashNextSib);
          setTimeout(() => newCard.classList.remove("stream-new"), 600);
          /* Use querySelector scoped to newCard — NOT getElementById — so we
             are guaranteed to get the new card's elements even if stale IDs
             somehow linger elsewhere in the document. */
          const meta = {
            card: newCard,
            stashedCard: existingCard,  // keep reference to discard after done
            statusBadge: newCard.querySelector("#prstatus-" + wid),
            viewBtn: newCard.querySelector("#prview-" + wid),
            barFill: null, barPct: null,
          };
          recordMeta[wid] = meta;
          currentRunWids.add(wid);
          return meta;
        }
        /* Existing card is not done (stale/failed run) — reset it in-place */
        existingCard.className = "pr-card stream-new";
        existingCard.innerHTML = `
          <div class="pr-header">
            <span class="pr-wid">${escHtml(wid)}</span>
            <span class="pr-status-badge pr-running" id="prstatus-${escHtml(wid)}">Processing…</span>
            <button class="pr-view-btn hidden" id="prview-${escHtml(wid)}"
              onclick="openSidePanel('${escHtml(wid)}','__RID__')">View Result &#8594;</button>
          </div>
          ${_stepsHtml(wid)}`;
        setTimeout(() => existingCard.classList.remove("stream-new"), 600);
        const meta = {
          card: existingCard,
          statusBadge: existingCard.querySelector("#prstatus-" + wid),
          viewBtn: existingCard.querySelector("#prview-" + wid),
          barFill: null, barPct: null,
        };
        recordMeta[wid] = meta;
        currentRunWids.add(wid);   // this wid now belongs to the current run
        return meta;
      }

      /* FEATURE 1: Insert file-group header if this wid belongs to a new file */
      _insertFileGroupHeader(wid);

      const card = document.createElement("div");
      card.className = "pr-card stream-new";
      card.id = "prcard-" + wid;
      /* Tag with file group for collapse/expand */
      var _cardFile = window._currentRunFileName || _widFileMap[wid] || null;
      if (!_cardFile) { var _bw = wid.replace(/_[a-zA-Z0-9_]+$/, ''); _cardFile = _widFileMap[_bw] || null; }
      if (_cardFile) card.setAttribute('data-file-group', _cardFile);
      setTimeout(() => card.classList.remove("stream-new"), 600);
      card.innerHTML = `
        <div class="pr-header">
          <span class="pr-wid">${escHtml(wid)}</span>
          <span class="pr-status-badge pr-running" id="prstatus-${escHtml(wid)}">Processing\u2026</span>
          <button class="pr-view-btn hidden" id="prview-${escHtml(wid)}"
            onclick="openSidePanel('${escHtml(wid)}','__RID__')">View Result &#8594;</button>
        </div>
        ${_stepsHtml(wid)}`;
      /* Insert new card at the top, above old restored cards */
      recordsWrap.insertBefore(card, _runInsertPoint);
      const meta = {
        card,
        statusBadge: card.querySelector("#prstatus-" + wid),
        viewBtn: card.querySelector("#prview-" + wid),
        barFill: null,
        barPct: null,
      };
      recordMeta[wid] = meta;
      currentRunWids.add(wid);   // this wid belongs to the current run
      return meta;
    }

    function _setRing(wid, ph, state) {
      const item = document.getElementById(`prstep-${wid}-${ph}`);
      if (!item) return;
      item.classList.remove("pr-step-done", "pr-step-active", "pr-step-pending");
      const phIdx = RING_ORDER.indexOf(ph);
      if (state === "done") {
        item.classList.add("pr-step-done");
        if (phIdx > 0) {
          const line = document.getElementById(`prline-${wid}-${phIdx - 1}`);
          if (line) line.classList.add("pr-step-line-done");
        }
      } else if (state === "active") {
        item.classList.add("pr-step-active");
      } else {
        item.classList.add("pr-step-pending");
      }
    }

    function setPhase(wid, phase, isDone) {
      const meta = recordMeta[wid]; if (!meta) return;
      if (meta.card.classList.contains("pr-card-done")) return;
      const colIdx = RING_ORDER.indexOf(phase);
      if (colIdx === -1) return;
      RING_ORDER.forEach((ph, i) => {
        if (i < colIdx) _setRing(wid, ph, "done");
        else if (i === colIdx) _setRing(wid, ph, isDone ? "done" : "active");
        else _setRing(wid, ph, "pending");
      });
      /* FIX 3+4b: advance the linear progress bar */
      const pct = isDone ? RING_PHASES[colIdx].pct : Math.max(0, RING_PHASES[colIdx].pct - 15);
      const fill = document.getElementById("prbar-" + wid);
      if (fill) fill.style.width = pct + "%";
    }

    /* ── FIX: updateCounter — centralised counter update used by all paths ── */
    function updateCounter() {
      // Use actual recordMeta count as authoritative fallback when totalWarnings is 0
      const knownTotal = totalWarnings > 0 ? totalWarnings : Object.keys(recordMeta).length;
      if (knownTotal > 0) {
        counterEl.textContent = `${doneCount} of ${knownTotal} records complete`;
        counterEl.className = "pr-counter" + (doneCount === knownTotal ? " pr-counter-done" : "");
      }
    }

    function markDone(wid, rid) {
      const meta = recordMeta[wid];
      if (!meta || meta.card.classList.contains("pr-card-done")) return;
      doneCount++;
      RING_ORDER.forEach(ph => _setRing(wid, ph, "done"));
      RING_PHASES.forEach((_, i) => { if (i < RING_PHASES.length - 1) { const ln = document.getElementById(`prline-${wid}-${i}`); if (ln) ln.classList.add("pr-step-line-done"); } });
      /* FIX 3+4c: always fill bar to 100% on completion */
      const fill = document.getElementById("prbar-" + wid); if (fill) fill.style.width = "100%";
      /* ROOT FIX: new run card is now confirmed done with the correct run_id.
         Discard the stashed old card — it is now superseded. */
      if (meta.stashedCard) {
        if (meta.stashedCard.parentNode) meta.stashedCard.parentNode.removeChild(meta.stashedCard);
        meta.stashedCard = null;
      }
      if (meta.statusBadge) {
        meta.statusBadge.className = "pr-status-badge pr-done";
        meta.statusBadge.textContent = "Complete";
      }
      meta.card.classList.add("pr-card-done");
      if (meta.viewBtn && rid) {
        const currentOnclick = meta.viewBtn.getAttribute("onclick") || "";
        /* Only replace the __RID__ placeholder — don't overwrite real run IDs
           already embedded in restored cards from a previous session */
        if (currentOnclick.includes("__RID__")) {
          meta.viewBtn.setAttribute("onclick", currentOnclick.replace("__RID__", rid));
        }
        meta.viewBtn.classList.remove("hidden");
      }
      // ── FIX: use centralised updateCounter instead of inline string ──
      updateCounter();
    }

    const PHASE_MAP = { "6a": "ph-6a", "6b": "ph-6b", "7": "ph-7", "8": "ph-8" };
    const es = new EventSource(`/api/progress/${jobId}`);
    es.onmessage = evt => {
      let msg; try { msg = JSON.parse(evt.data); } catch { return; }
      if (msg.type === "heartbeat") return;
      if (msg.type === "status") { if (statusLn && msg.label) statusLn.textContent = msg.label; return; }

      // ── FIX: handle total_update event (emitted by server when [N/M] line seen) ──
      if (msg.type === "total_update" && msg.total > 0) {
        totalWarnings = msg.total;
        updateCounter();
        return;
      }

      if (msg.phase && PHASE_MAP[msg.phase]) {
        const phEl = document.getElementById(PHASE_MAP[msg.phase]);
        if (phEl) {
          if (msg.type === "phase_start") {
            document.querySelectorAll(".phase-item").forEach(el => el.classList.remove("active"));
            phEl.classList.add("active");
            const det = phEl.querySelector(".phase-detail");
            if (det) det.textContent = plainDetail(msg.detail);
            /* Update pipeline status tag colour: red=phases 1-2, yellow=phases 3-4 */
            const _sdot2 = document.getElementById("pipeline-status-dot");
            const _stag2 = document.getElementById("pipeline-status-tag");
            const _slbl2 = document.getElementById("pipeline-status-label");
            const _ph = msg.phase || "";
            if (_ph === "6a" || _ph === "6b") {
              if (_sdot2) { _sdot2.style.background = "var(--red,#c0392b)"; _sdot2.style.animation = "pulse-dot 1.2s infinite"; }
              if (_stag2) { _stag2.style.background = "rgba(192,57,43,.07)"; _stag2.style.color = "var(--red,#c0392b)"; _stag2.style.borderColor = "rgba(192,57,43,.2)"; }
              if (_slbl2) _slbl2.textContent = "Reading & Matching…";
            } else if (_ph === "7") {
              if (_sdot2) { _sdot2.style.background = "#f59e0b"; _sdot2.style.animation = "pulse-dot 1.2s infinite"; }
              if (_stag2) { _stag2.style.background = "rgba(245,158,11,.07)"; _stag2.style.color = "#b45309"; _stag2.style.borderColor = "rgba(245,158,11,.25)"; }
              if (_slbl2) _slbl2.textContent = "Generating Fixes…";
            } else if (_ph === "8") {
              if (_sdot2) { _sdot2.style.background = "#f59e0b"; _sdot2.style.animation = "pulse-dot 1.2s infinite"; }
              if (_stag2) { _stag2.style.background = "rgba(245,158,11,.07)"; _stag2.style.color = "#b45309"; _stag2.style.borderColor = "rgba(245,158,11,.25)"; }
              if (_slbl2) _slbl2.textContent = "Quality Check…";
            }
            _stopElapsedTicker();
            if (msg.phase === "7") {
              const _t7start = Date.now();
              if (window._phase7Timer) clearInterval(window._phase7Timer);
              window._phase7Timer = setInterval(() => {
                const s = Math.floor((Date.now() - _t7start) / 1000);
                const m = Math.floor(s / 60);
                const ss = String(s % 60).padStart(2, "0");
                if (statusLn) statusLn.textContent =
                  `Generating fix suggestions… ${m > 0 ? m + "m " + ss + "s" : s + "s"} elapsed`;
              }, 1000);
            }
          }
          else if (msg.type === "phase_done") {
            phEl.classList.remove("active"); phEl.classList.add("done");
            const b = phEl.querySelector(".phase-badge"); if (b) b.textContent = "\u2713";
            if (msg.phase === "6a") _stopElapsedTicker();
            if (msg.phase === "7" && window._phase7Timer) { clearInterval(window._phase7Timer); window._phase7Timer = null; }
          }
        }
      }

      if (msg.label && statusLn) statusLn.textContent = plainEnglish(msg.label, msg.detail);
      else if (msg.type === "detail" && msg.detail && statusLn) statusLn.textContent = plainDetail(msg.detail);

      // ── FIX: update totalWarnings from ANY message that carries msg.total ──
      // This covers phase_done(6a) with total, warning_start with total, and done event.
      if (msg.total && msg.total > 0) {
        totalWarnings = msg.total;
        updateCounter();
      }

      // Legacy pct-based estimate — only used as last resort when no total arrived yet
      if (msg.type === "warning_start" && typeof msg.pct === "number" && totalWarnings === 0 && msg.pct > 0) {
        const estimated = Math.round(100 / msg.pct);
        if (estimated > 0) { totalWarnings = estimated; updateCounter(); }
      }

      if (msg.warning_id) {
        const wid = msg.warning_id; ensureRecord(wid);
        if (msg.type === "warning_start") {
          const ph = msg.phase || "7";
          if (ph === "8") { ["6a", "6b", "7"].forEach(p => setPhase(wid, p, true)); setPhase(wid, "8", false); }
          else if (ph === "7") { ["6a", "6b"].forEach(p => setPhase(wid, p, true)); setPhase(wid, "7", false); }
          else if (ph === "6b") { setPhase(wid, "6a", true); setPhase(wid, "6b", false); }
          else setPhase(wid, ph, false);
          recordMeta[wid].card.scrollIntoView({ behavior: "smooth", block: "nearest" });
        } else if (msg.type === "warning_done") {
          const donePh = msg.phase || "7";
          setPhase(wid, donePh, true);
        }
      }

      if (msg.type === "done") {
        es.close(); _stopElapsedTicker();
        if (window._phase7Timer) { clearInterval(window._phase7Timer); window._phase7Timer = null; }
        const targetId = msg.run_id || runId || jobId;

        // ── FIX: use total from done event if we still don't have one ──
        if (msg.total && msg.total > 0) totalWarnings = msg.total;

        const phDone = document.getElementById("ph-done");
        if (phDone) {
          phDone.classList.add("active");
          setTimeout(() => {
            phDone.classList.remove("active"); phDone.classList.add("done");
            const b = phDone.querySelector(".phase-badge"); if (b) b.textContent = "\u2713";
            /* Update the "Waiting…" detail text to show report is ready */
            const det = phDone.querySelector(".phase-detail"); if (det) det.textContent = "View below \u2193";
          }, 400);
        }
        document.querySelectorAll(".phase-item:not(#ph-done)").forEach(el => { el.classList.remove("active"); el.classList.add("done"); const b = el.querySelector(".phase-badge"); if (b) b.textContent = "\u2713"; });
        /* Update pipeline status tag to green */
        const _stag = document.getElementById("pipeline-status-tag");
        const _sdot = document.getElementById("pipeline-status-dot");
        const _slbl = document.getElementById("pipeline-status-label");
        if (_stag) { _stag.style.background = "rgba(16,185,129,.08)"; _stag.style.color = "#065f46"; _stag.style.borderColor = "rgba(16,185,129,.25)"; }
        if (_sdot) { _sdot.style.background = "#10b981"; _sdot.style.animation = "none"; }
        if (_slbl) _slbl.textContent = "Report Ready";

        /* Update live file-group header status badge to ✓ Done */
        if (window._currentRunFileName) {
          var _liveHdr = document.getElementById('pr-file-hdr-' + window._currentRunFileName.replace(/[^a-zA-Z0-9]/g, '_'));
          if (_liveHdr) {
            var _statusEl = _liveHdr.querySelector('.pr-fhdr-status');
            if (_statusEl) {
              _statusEl.className = 'pr-fhdr-status';
              _statusEl.innerHTML = '&#10003; Done &middot; ' + currentRunWids.size + ' warning' + (currentRunWids.size !== 1 ? 's' : '');
            }
          }
        }

        /* Only mark done and update View Result buttons for wids that belong to THIS run.
           Using Object.keys(recordMeta) would include wids from previous restored runs,
           causing their View Result buttons to point at the new run_id → "Record not found". */
        currentRunWids.forEach(wid => {
          const meta = recordMeta[wid];
          if (meta && !meta.card.classList.contains("pr-card-done")) {
            setPhase(wid, "8", true);
          }
          markDone(wid, targetId);
        });

        if (statusLn) statusLn.textContent = "All done! Click any record to view its result.";

        // ── FIX: final counter uses actual record count as the ground truth ──
        const finalCount = totalWarnings > 0 ? totalWarnings : currentRunWids.size;
        counterEl.textContent = `All ${finalCount} records complete`;
        counterEl.className = "pr-counter pr-counter-done";

        // Persist to sessionStorage — only store THIS run's wids under THIS run's id
        try {
          var _sr = JSON.parse(sessionStorage.getItem("misra_completed_runs") || "[]");
          _sr = _sr.filter(function (r) { return r.runId !== targetId; });
          /* Also persist wid→file mapping for this run so Back-nav can rebuild headers */
          var _runWidFiles = {};
          currentRunWids.forEach(function (wid) {
            var fn = window._currentRunFileName || _widFileMap[wid] || null;
            if (!fn) { var bw = wid.replace(/_[a-zA-Z0-9_]+$/, ''); fn = _widFileMap[bw] || null; }
            if (fn) _runWidFiles[wid] = fn;
          });
          _sr.push({ runId: targetId, total: finalCount, wids: [...currentRunWids], widFiles: _runWidFiles });
          sessionStorage.setItem("misra_completed_runs", JSON.stringify(_sr.slice(-10)));
          /* Rebuild nav map so Next/Prev buttons are up to date */
          _buildSpNavMap();
        } catch (e) { }

        /* BUG2 FIX: Mark completed files in _ranFiles FIRST, then persist —
           previously the save happened before _ranFiles.add(), so the just-
           completed file was never included in ranFiles on back navigation. */
        if (window._currentIsRunAll) {
          cFilesList.forEach((_, i) => _ranFiles.add(i));
        } else if (window._currentFileIdx !== null && window._currentFileIdx !== undefined) {
          _ranFiles.add(window._currentFileIdx);
        }

        /* Persist file names and ran state so Back navigation can restore file map */
        try {
          var _allNames = cFilesList.map(function (f) { return f.name; });
          var _ranNames = cFilesList.filter(function (_, i) { return _ranFiles.has(i); }).map(function (f) { return f.name; });
          /* FIX 1: also persist parsedExcelData so restored cards can show warning details */
          sessionStorage.setItem("misra_file_state", JSON.stringify({ allFiles: _allNames, ranFiles: _ranNames, parsedExcelData: parsedExcelData }));
        } catch (e) { }

        /* Refresh the file map UI so ran files show as done, others stay runnable */
        cFilesList.forEach(function (_, i) {
          const card = document.getElementById("fmap-" + i);
          if (!card) return;
          const btn = card.querySelector(".fmap-run-btn");
          if (_ranFiles.has(i)) {
            /* Mark as completed — static, cannot re-run */
            card.classList.add("fmap-ran");
            if (btn) { btn.disabled = true; btn.textContent = "✓ Done"; btn.classList.add("fmap-done-btn"); }
          } else {
            /* Pending files: restore their original button so they can still be run.
               Use innerHTML (not textContent) to restore the SVG play icon. */
            if (btn) {
              btn.disabled = false;
              btn.innerHTML = '<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run This File';
              btn.classList.remove("fmap-done-btn");
            }
          }
        });

        /* Re-enable upload card so user can run remaining files */
        const uploadCard2 = document.getElementById("upload-card");
        if (uploadCard2) { uploadCard2.style.opacity = "1"; uploadCard2.style.pointerEvents = "auto"; }

        /* No back-to-upload button on progress panel - user can scroll up to upload panel */
      }

      if (msg.type === "error") {
        es.close(); _stopElapsedTicker();
        document.querySelectorAll(".phase-item.active").forEach(el => { el.classList.remove("active"); el.classList.add("error"); });
        if (statusLn) statusLn.textContent = "Something went wrong. Please try again.";
        const ep = document.createElement("div"); ep.className = "error-panel mt-16"; ep.textContent = msg.message || msg.detail || "Unknown error"; progressPanel.appendChild(ep);
        resetUI();
      }
    };
    es.onerror = () => { es.close(); _stopElapsedTicker(); if (statusLn) statusLn.textContent = "Connection lost. Please refresh and try again."; };
  }

  function plainEnglish(label, detail) {
    if (!label) return plainDetail(detail || "");
    const L = label.toLowerCase();
    if (L.includes("launch")) return "Starting up \u2014 loading AI model\u2026";
    if (L.includes("reading file") || L.includes("parsing")) return "Loading your files\u2026";
    if (L.includes("looking up rules") || L.includes("retrieving misra")) return "Matching rules to warnings\u2026";
    if (L.includes("fix suggestion") || L.includes("generating fix")) return "Generating fixes with AI\u2026";
    if (L.includes("quality check") || L.includes("evaluating fix")) return "Verifying fix quality\u2026";
    if (L.includes("preparing") || L.includes("pipeline complete") || L.includes("report ready")) return "Preparing your report\u2026";
    if (L.includes("processing:")) return "Generating fix for warning " + label.replace(/.*processing:\s*/i, "").replace(/\s*\(.*\)/, "");
    if (L.includes("looking up rules:")) return "Looking up rules for warning " + label.replace(/.*looking up rules:\s*/i, "");
    if (L.includes("context:")) return "Rules matched \u2014 " + label.replace(/.*context:\s*/i, "");
    if (L.includes("fix generated")) return "Fix generated";
    if (L.includes("file read") || L.includes("parsing complete")) return "Files loaded";
    if (L.includes("rule lookup complete")) return "Rules matched";
    if (L.includes("fix suggestions complete")) return "Fixes generated";
    if (L.includes("all done") || L.includes("analysis complete")) return "All done! Click any record to view its result.";
    return plainDetail(label + (detail ? " \u2014 " + detail : ""));
  }
  function plainDetail(d) {
    if (!d) return "";
    return d
      .replace(/querying\s+(qdrant|faiss|bge|embedding)[^,\n]*/gi, "matching rules")
      .replace(/qdrant|faiss/gi, "rule database")
      .replace(/bge[\s-]?embeddings?/gi, "AI search")
      .replace(/embeddings?/gi, "AI search")
      .replace(/llm|llama|mistral-?\d*b?/gi, "AI")
      .replace(/self-critique pass/gi, "verifying fix quality")
      .replace(/parsed_warnings?/gi, "warnings read")
      .replace(/reading excel \+ source files/gi, "loading your files")
      .replace(/phase\s*6a/gi, "Step 1")
      .replace(/phase\s*6b/gi, "Step 2")
      .replace(/phase\s*7/gi, "Step 3")
      .replace(/phase\s*8/gi, "Step 4");
  }
}

/* ============================================================
   FILE GROUP COLLAPSE/EXPAND — module-level so restored cards
   can call it on page load before listenProgress() ever runs
   ============================================================ */
window._toggleFileGroup = function (fname) {
  var hdr = document.getElementById('pr-file-hdr-' + fname.replace(/[^a-zA-Z0-9]/g, '_'));
  if (!hdr) return;
  var isCollapsed = hdr.getAttribute('data-collapsed') === 'true';
  var rw = document.getElementById('per-record-wrap');
  /* Query ALL cards and file-group headers that belong to this group */
  var selector = '.pr-card[data-file-group="' + fname + '"]';
  var cards = rw ? rw.querySelectorAll(selector) : document.querySelectorAll(selector);
  cards.forEach(function (c) { c.style.display = isCollapsed ? '' : 'none'; });
  hdr.setAttribute('data-collapsed', isCollapsed ? 'false' : 'true');
  var chev = hdr.querySelector('.pr-file-grp-chevron');
  if (chev) chev.style.transform = isCollapsed ? '' : 'rotate(-90deg)';
};

/* ============================================================
   FEATURE 2: Side panel wid navigation (Prev/Next per file group)
   ============================================================ */
/* _spNavMap: { fileName: [wid1, wid2, ...] } — ordered list per file */
window._spNavMap = window._spNavMap || {};
window._spNavRidMap = window._spNavRidMap || {};  /* wid -> rid */

/* Build/update nav map from completed runs in sessionStorage */
function _buildSpNavMap() {
  window._spNavMap = {};
  window._spNavRidMap = {};
  try {
    var saved = JSON.parse(sessionStorage.getItem("misra_completed_runs") || "[]");
    saved.forEach(function (run) {
      var rid = run.runId;
      var widFiles = run.widFiles || {};
      (run.wids || []).forEach(function (wid) {
        var fn = widFiles[wid] || "__unknown__";
        window._spNavMap[fn] = window._spNavMap[fn] || [];
        if (window._spNavMap[fn].indexOf(wid) === -1) window._spNavMap[fn].push(wid);
        window._spNavRidMap[wid] = rid;
      });
    });
  } catch (_e) { }
}
_buildSpNavMap();

/* Get prev/next wid for a given wid within its file group */
function _spGetNavInfo(wid) {
  var fn = null, idx = -1;
  Object.keys(window._spNavMap).forEach(function (f) {
    var i = window._spNavMap[f].indexOf(wid);
    if (i !== -1) { fn = f; idx = i; }
  });
  if (!fn || idx === -1) return { prev: null, next: null, isLast: true, fileName: null };
  var arr = window._spNavMap[fn];
  return {
    prev: idx > 0 ? arr[idx - 1] : null,
    next: idx < arr.length - 1 ? arr[idx + 1] : null,
    isLast: idx === arr.length - 1,
    fileName: fn,
    total: arr.length,
    position: idx + 1
  };
}

window._spNavigateTo = function (wid) {
  var rid = window._spNavRidMap[wid] || "";
  if (!rid) return;
  if (typeof window.openSidePanel === 'function') window.openSidePanel(wid, rid);
};
var _ruleState = { selected: new Set(), overrides: {}, built: false };
window._ruleState = _ruleState;

function cssId(id) { return id.replace(/\./g, "_").replace(/\s/g, "-"); }

window.openSettingsModal = function () {
  const modal = document.getElementById("settings-modal");
  if (!modal) return;
  modal.classList.remove("hidden");
  if (!_ruleState.built) { buildModalRuleList(); _ruleState.built = true; }
  document.body.style.overflow = "hidden";
};

window.closeSettingsModal = function () {
  const modal = document.getElementById("settings-modal");
  if (modal) modal.classList.add("hidden");
  document.body.style.overflow = "";
};

window.applyAndCloseModal = function () {
  try {
    sessionStorage.setItem("rule_selected", JSON.stringify([..._ruleState.selected]));
    sessionStorage.setItem("rule_overrides", JSON.stringify(_ruleState.overrides));
  } catch (e) { }
  closeSettingsModal();
};

window.modalPreset = function (btn) {
  document.querySelectorAll(".preset-pill").forEach(b => b.classList.remove("pp-active"));
  btn.classList.add("pp-active");
  const preset = btn.dataset.preset;
  _ruleState.selected.clear();
  if (preset === "ALL") RULES_DATA.forEach(r => _ruleState.selected.add(r.id));
  RULES_DATA.forEach(r => {
    const cb = document.getElementById("mrcb-" + cssId(r.id));
    const row = document.getElementById("mrow-" + cssId(r.id));
    const sel = _ruleState.selected.has(r.id);
    if (cb) cb.checked = sel;
    if (row) row.classList.toggle("mrow-selected", sel);
  });
  updateModalSummary();
};

function buildModalRuleList() {
  const container = document.getElementById("modal-rule-list");
  if (!container) return;
  container.innerHTML = "";

  const rulesOnly = RULES_DATA.filter(r => !r.is_dir);

  const sorted = [...rulesOnly].sort((a, b) => {
    const parse = id => id.split(".").map(Number);
    const [a1, a2] = parse(a.id), [b1, b2] = parse(b.id);
    return a1 !== b1 ? a1 - b1 : (a2 || 0) - (b2 || 0);
  });

  sorted.forEach(r => {
    const isSel = _ruleState.selected.has(r.id);
    const ov = _ruleState.overrides[r.id] || null;
    const effSev = ov || r.sev;
    const sevLabel = { M: "Mandatory", R: "Required", A: "Advisory" };

    const row = document.createElement("div");
    row.className = "mrow" + (isSel ? " mrow-selected" : "");
    row.id = "mrow-" + cssId(r.id);

    const mraHtml = ["M", "R", "A"].map(s => {
      const isActive = isSel && effSev === s;
      return `<button class="mra-btn${isActive ? " mra-active mra-" + s.toLowerCase() : ""}"
        onclick="setRuleSev('${r.id}','${s}',this)"
        title="${sevLabel[s]}">${s}</button>`;
    }).join("");

    row.innerHTML = `
      <label class="mrow-check-label">
        <input type="checkbox" class="rc-cb" id="mrcb-${cssId(r.id)}"
          ${isSel ? "checked" : ""}
          onchange="toggleModalRule('${r.id}',this.checked)">
        <span class="mrow-rule-id">${r.is_dir ? "Dir " : "Rule "}${r.id}</span>
      </label>
      <div class="mrow-mra ${isSel ? "" : "mra-disabled"}" id="mra-${cssId(r.id)}">${mraHtml}</div>`;

    container.appendChild(row);
  });

  updateModalSummary();
}

window.toggleModalRule = function (id, checked) {
  if (checked) {
    _ruleState.selected.add(id);
    if (!_ruleState.overrides[id]) _ruleState.overrides[id] = (RULES_DATA.find(r => r.id === id) || {}).sev || "R";
  } else {
    _ruleState.selected.delete(id);
  }
  const row = document.getElementById("mrow-" + cssId(id));
  const mra = document.getElementById("mra-" + cssId(id));
  if (row) row.classList.toggle("mrow-selected", checked);
  if (mra) mra.classList.toggle("mra-disabled", !checked);
  _refreshMraButtons(id);
  updateModalSummary();
};

window.setRuleSev = function (id, sev, btn) {
  if (_ruleState.overrides[id] === sev && _ruleState.selected.has(id)) {
    _ruleState.selected.delete(id);
    delete _ruleState.overrides[id];
    const cb = document.getElementById("mrcb-" + cssId(id));
    if (cb) cb.checked = false;
    const row = document.getElementById("mrow-" + cssId(id));
    if (row) row.classList.remove("mrow-selected");
    const mra = document.getElementById("mra-" + cssId(id));
    if (mra) mra.classList.add("mra-disabled");
    _refreshMraButtons(id);
    updateModalSummary();
    return;
  }
  _ruleState.selected.add(id);
  _ruleState.overrides[id] = sev;
  const cb = document.getElementById("mrcb-" + cssId(id));
  if (cb) cb.checked = true;
  const row = document.getElementById("mrow-" + cssId(id));
  if (row) row.classList.add("mrow-selected");
  const mra = document.getElementById("mra-" + cssId(id));
  if (mra) mra.classList.remove("mra-disabled");
  _refreshMraButtons(id);
  updateModalSummary();
};

function _refreshMraButtons(id) {
  const mra = document.getElementById("mra-" + cssId(id));
  if (!mra) return;
  const ov = _ruleState.overrides[id] || null;
  const sel = _ruleState.selected.has(id);
  mra.querySelectorAll(".mra-btn").forEach(btn => {
    const s = btn.textContent.trim();
    const isActive = sel && ov === s;
    btn.className = "mra-btn" + (isActive ? " mra-active mra-" + s.toLowerCase() : "");
  });
}

window.filterModalRules = function () {
  const q = ((document.getElementById("modal-rule-search") || {}).value || "").trim().toLowerCase();
  RULES_DATA.filter(r => !r.is_dir).forEach(r => {
    const row = document.getElementById("mrow-" + cssId(r.id));
    if (!row) return;
    row.style.display = (!q || r.id.toLowerCase().includes(q)) ? "" : "none";
  });
};

function updateModalSummary() {
  const tot = _ruleState.selected.size;
  const sc = document.getElementById("modal-sel-count");
  if (sc) sc.textContent = tot;
}

/* ============================================================
   SIDE PANEL — module-level (works after Back navigation)
   openSidePanel must live here so restored View Result buttons
   can call it even when listenProgress has never run.
   ============================================================ */

var sidePanel = null; // module-level reference, set by _initSidePanel()

function _initSidePanel() {
  var _existing = document.getElementById("pr-side-panel");
  if (_existing) { sidePanel = _existing; return; }
  var _sp = document.createElement("div");
  _sp.id = "pr-side-panel";
  _sp.className = "pr-side-panel";
  _sp.innerHTML = '<div class="pr-side-inner">'
    + '<div class="pr-side-header">'
    + '<div class="pr-side-title" id="pr-side-title">Result</div>'
    + '<button class="pr-side-close" onclick="closeSidePanel()" title="Close">&#x2715;</button>'
    + '</div>'
    + '<div class="pr-side-body" id="pr-side-body">'
    + '<div class="pr-side-loading"><div class="ld"></div><div class="ld"></div><div class="ld"></div>'
    + '<span class="ld-text">Loading…</span></div>'
    + '</div></div>'
    + '<div class="pr-side-backdrop" onclick="closeSidePanel()"></div>';
  document.body.appendChild(_sp);
  sidePanel = _sp;
}

window.closeSidePanel = function () {
  var _sp = document.getElementById("pr-side-panel");
  if (_sp) { _sp.classList.remove("pr-side-open"); document.body.classList.remove("pr-panel-open"); }
  window._spOpenedFromRR = false;
};

/* FIX 4: Restore button states in side panel after Back navigation reopens it */
function _spRestoreActionState(wid) {
  var committed = (window._commitResults || {})[wid];
  var noChange = (window._noChangeResults || {})[wid];
  var commitBtn = document.getElementById("commit-btn-" + wid);
  var goBtn = document.getElementById("go-without-btn-" + wid);
  var patchWrap = document.getElementById("patched-wrap-" + wid);

  if (noChange) {
    if (commitBtn) { commitBtn.disabled = true; }
    if (goBtn) { goBtn.textContent = "\u2713 Kept Original"; goBtn.disabled = true; goBtn.classList.add("go-without-btn-done"); }
    return;
  }

  if (committed) {
    if (commitBtn) { commitBtn.textContent = "\u2713 Committed"; commitBtn.classList.add("committed"); commitBtn.disabled = true; }
    if (goBtn) { goBtn.disabled = true; }

    /* If patchedCode was not yet loaded (came from sessionStorage only), fetch it now */
    if (committed._needsServerLoad) {
      fetch("/api/committed/" + encodeURIComponent(wid)).then(function (r) {
        if (!r.ok) return;
        return r.json();
      }).then(function (d) {
        if (!d || !d.committed || !d.patched_code) return;
        committed.patchedCode = d.patched_code;
        committed.afterCode = d.patched_code;
        committed._needsServerLoad = false;
        /* Show patched file in side panel */
        if (patchWrap) {
          patchWrap.classList.remove("hidden");
          var patchTitle = document.getElementById("patched-file-title-" + wid);
          var patchBlock = document.getElementById("patched-code-" + wid);
          if (patchTitle) patchTitle.textContent = "\u2713 Full patched file: " + (committed.originalFile || "source.c");
          if (patchBlock) {
            var pStart = committed.patchLineStart || 0, pEnd = pStart ? pStart + (committed.patchLineCount || 0) - 1 : 0;
            patchBlock.innerHTML = d.patched_code.split("\n").map(function (ln, i) {
              var num = i + 1, isChg = pStart > 0 && num >= pStart && num <= pEnd;
              return '<div class="code-row' + (isChg ? ' patch-highlight' : '') + '"><span class="ln-num">' + num + '</span><span class="ln-code">' + escHtml(ln) + '</span></div>';
            }).join("");
          }
        }
      }).catch(function () { });
    } else if (committed.patchedCode && patchWrap) {
      /* Already have patchedCode in memory — show immediately */
      patchWrap.classList.remove("hidden");
      var pTitle = document.getElementById("patched-file-title-" + wid);
      var pBlock = document.getElementById("patched-code-" + wid);
      if (pTitle) pTitle.textContent = "\u2713 Full patched file: " + (committed.originalFile || "source.c");
      if (pBlock) {
        var ps = committed.patchLineStart || 0, pe = ps ? ps + (committed.patchLineCount || 0) - 1 : 0;
        pBlock.innerHTML = committed.patchedCode.split("\n").map(function (ln, i) {
          var num = i + 1, isChg = ps > 0 && num >= ps && num <= pe;
          return '<div class="code-row' + (isChg ? ' patch-highlight' : '') + '"><span class="ln-num">' + num + '</span><span class="ln-code">' + escHtml(ln) + '</span></div>';
        }).join("");
      }
      /* Show undo button */
      if (commitBtn && !document.getElementById("undo-inline-" + wid)) {
        var _undoBtn = document.createElement("button");
        _undoBtn.id = "undo-inline-" + wid;
        _undoBtn.textContent = "\u21A9 Undo";
        _undoBtn.title = "Revert this fix and restore original file";
        _undoBtn.style.cssText = "margin-left:8px;background:#dc2626;color:#fff;border:none;padding:3px 9px;border-radius:5px;font-size:11px;font-weight:600;cursor:pointer;vertical-align:middle;";
        _undoBtn.onclick = function () { undoCommit(wid); };
        commitBtn.parentElement && commitBtn.parentElement.appendChild(_undoBtn);
      }
    }
  }
}

/* FEATURE 2: Toggle edit mode for the after-code block in side panel */
window.toggleFixEdit = function (wId) {
  var codeEl = document.getElementById("after-code-" + wId);
  var editEl = document.getElementById("after-edit-area-" + wId);
  var editBtn = document.getElementById("sp-edit-btn-" + wId);
  var commitBtn = document.getElementById("commit-btn-" + wId);
  if (!codeEl || !editEl) return;
  var isEditing = !editEl.classList.contains("hidden");
  if (isEditing) {
    /* ── SAVE EDIT ── */
    var editedText = editEl.value;
    window._fixData = window._fixData || {};
    if (window._fixData[wId]) window._fixData[wId]._editedCode = editedText;
    /* Render preview of edited code */
    codeEl.innerHTML = renderAfterCode(editedText);
    codeEl.classList.remove("hidden");
    editEl.classList.add("hidden");
    if (editBtn) { editBtn.textContent = "\u2702 Edit"; editBtn.classList.remove("sp-edit-btn-active"); }
    /* Re-enable commit button so user can commit their edited version.
       If it was previously committed, reset it to allow re-commit of the new edit. */
    if (commitBtn) {
      commitBtn.disabled = false;
      commitBtn.textContent = "\u2B06 Commit Fix to File";
      commitBtn.classList.remove("committed");
    }
  } else {
    /* ── ENTER EDIT MODE ── */
    var data = (window._fixData || {})[wId];
    var currentCode = data && data._editedCode
      ? data._editedCode
      : extractAfterCode((data && data.fixes) ? data.fixes[data.selectedIdx || 0] : null);
    editEl.value = currentCode;
    codeEl.classList.add("hidden");
    editEl.classList.remove("hidden");
    editEl.focus();
    if (editBtn) { editBtn.textContent = "\u2714 Save Edit"; editBtn.classList.add("sp-edit-btn-active"); }
    /* Disable commit button while user is actively editing — must save edit first */
    if (commitBtn) { commitBtn.disabled = true; }
  }
};

/* FEATURE 3: Mark warning as "no change" — update Review Report without committed patch */
window.goWithoutChange = function (wId) {
  window._noChangeResults = window._noChangeResults || {};
  window._noChangeResults[wId] = true;
  /* Persist so Back navigation restores this state */
  try {
    var _nc = JSON.parse(sessionStorage.getItem("misra_no_change") || "{}");
    _nc[wId] = true;
    sessionStorage.setItem("misra_no_change", JSON.stringify(_nc));
  } catch (_e) { }
  /* Update side panel buttons */
  var commitBtn = document.getElementById("commit-btn-" + wId);
  var goBtn = document.getElementById("go-without-btn-" + wId);
  if (goBtn) { goBtn.textContent = "\u2713 Kept Original"; goBtn.disabled = true; goBtn.classList.add("go-without-btn-done"); }
  if (commitBtn) { commitBtn.disabled = true; }
  /* Update Review Report AFTER block to show no-change state */
  _rrMarkNoChange(wId);
  /* Auto-close side panel if it was opened from the Review Report awaiting-decision button */
  if (window._spOpenedFromRR) {
    setTimeout(function () { window.closeSidePanel(); }, 350);
  }
};

function _rrMarkNoChange(wId) {
  var labelEl = document.getElementById("rr-after-label-" + wId);
  var codeEl = document.getElementById("rr-after-code-" + wId);
  if (!labelEl && !codeEl) return; /* card not open yet — will be set on render */
  if (labelEl) {
    labelEl.style.color = "#92400e";
    labelEl.innerHTML = '<span style="color:#92400e;">\u26A0 NO CHANGE APPLIED</span> <span style="font-size:10px;font-weight:600;background:rgba(234,179,8,.12);color:#92400e;padding:1px 8px;border-radius:10px;margin-left:4px;">Kept Original</span>';
  }
  if (codeEl) {
    codeEl.innerHTML = '<div style="padding:16px 14px;color:var(--text-muted);font-size:13px;font-style:italic;display:flex;align-items:center;gap:8px;">'
      + '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
      + 'No fix applied &mdash; original code retained as-is.</div>';
  }
}

/* Reset Review Report card to AWAITING DECISION after undo */
function _rrResetToAwaiting(wId) {
  var labelEl = document.getElementById("rr-after-label-" + wId);
  var codeEl = document.getElementById("rr-after-code-" + wId);
  var blockEl = document.getElementById("rr-after-block-" + wId);
  var chipsRow = document.getElementById("fixchips-" + wId);
  var dlEl = document.getElementById("rr-download-" + wId);
  if (!labelEl && !codeEl) return; /* card not open — will render correctly when opened */
  var _fd = (window._fixData || {})[wId];
  var _spRid = _fd ? (_fd.rid || window.MISRA_RUN_ID || "") : (window.MISRA_RUN_ID || "");
  if (labelEl) { labelEl.style.color = "#92400e"; labelEl.innerHTML = '<span style="color:#92400e;">\u23F3 AWAITING DECISION</span>'; }
  if (blockEl) blockEl.style.borderColor = "rgba(234,179,8,.35)";
  if (codeEl) {
    codeEl.innerHTML = '<div style="padding:20px 16px;display:flex;flex-direction:column;align-items:flex-start;gap:10px;">'
      + '<div style="font-size:13px;color:var(--text-muted);font-style:italic;">Fix was reverted. No action taken for this warning.</div>'
      + '<div style="font-size:12px;color:var(--text-sub);">Open View Results to select a new fix or choose to keep the original code.</div>'
      + '<button onclick="window._rrOpenViewResult(\'' + escHtml(wId) + '\',\'' + escHtml(_spRid) + '\')" '
      + 'style="background:#1e40af;color:#fff;border:none;padding:7px 16px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;gap:6px;">'
      + '&#8594; Open View Results for #' + escHtml(wId) + '</button>'
      + '</div>';
  }
  if (dlEl) dlEl.innerHTML = "";
  if (chipsRow) chipsRow.style.display = "none";
}

window.openSidePanel = async function (wid, rid) {
  /* Safety: ensure side panel DOM exists even if listenProgress never ran */
  if (!sidePanel) _initSidePanel();
  sidePanel.classList.add("pr-side-open"); document.body.classList.add("pr-panel-open");

  /* FEATURE 2: Update title + nav buttons */
  var navInfo = _spGetNavInfo(wid);
  var titleEl = document.getElementById("pr-side-title");
  if (titleEl) titleEl.textContent = "Warning " + wid
    + (navInfo.total > 1 ? "  (" + navInfo.position + "/" + navInfo.total + ")" : "");
  /* Render prev/next nav bar */
  var navBar = document.getElementById("pr-side-nav");
  if (!navBar) {
    navBar = document.createElement("div");
    navBar.id = "pr-side-nav";
    navBar.style.cssText = "display:flex;align-items:center;gap:6px;padding:0 16px 10px;border-bottom:1px solid var(--border);";
    var hdr = document.querySelector(".pr-side-header");
    if (hdr && hdr.parentNode) hdr.parentNode.insertBefore(navBar, hdr.nextSibling);
  }
  var prevHtml = navInfo.prev
    ? '<button onclick="window._spNavigateTo(\'' + escHtml(navInfo.prev) + '\')" style="background:none;border:1px solid var(--border);border-radius:6px;padding:3px 10px;font-size:12px;font-weight:600;cursor:pointer;color:var(--text-sub);display:inline-flex;align-items:center;gap:4px;">&#8592; Prev</button>'
    : '<button disabled style="background:none;border:1px solid var(--border);border-radius:6px;padding:3px 10px;font-size:12px;cursor:not-allowed;color:var(--text-muted);opacity:.4;">&#8592; Prev</button>';
  var nextHtml = navInfo.next
    ? '<button onclick="window._spNavigateTo(\'' + escHtml(navInfo.next) + '\')" style="background:none;border:1px solid var(--border);border-radius:6px;padding:3px 10px;font-size:12px;font-weight:600;cursor:pointer;color:var(--text-sub);display:inline-flex;align-items:center;gap:4px;">Next &#8594;</button>'
    : '<button disabled style="background:none;border:1px solid var(--border);border-radius:6px;padding:3px 10px;font-size:12px;cursor:not-allowed;color:var(--text-muted);opacity:.4;">Next &#8594;</button>';
  var fileLabel = navInfo.fileName && navInfo.fileName !== "__unknown__"
    ? '<span style="font-size:11px;color:var(--text-muted);flex:1;text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + escHtml(navInfo.fileName) + '</span>'
    : '<span style="flex:1;"></span>';
  navBar.innerHTML = prevHtml + fileLabel + nextHtml;
  /* Store current wid on panel so _buildSpNavMap can reference it */
  sidePanel.setAttribute('data-current-wid', wid);

  const body = document.getElementById("pr-side-body");
  body.innerHTML = `<div class="pr-side-loading"><div class="ld"></div><div class="ld"></div><div class="ld"></div><span class="ld-text">Loading result\u2026</span></div>`;
  try {
    const resp = await fetch("/api/result/" + rid);
    const data = await resp.json();
    const warnings = data.warnings || [];
    const w = warnings.find(x => String(x.warning_id) === String(wid)) || warnings[0];
    if (!w) { body.innerHTML = `<div class="error-panel">Record not found.</div>`; return; }
    body.innerHTML = buildSidePanelContent(w, rid, navInfo.isLast);
    /* FIX 4: After rendering, restore committed/noChange button states from memory */
    _spRestoreActionState(wid);
  } catch (e) {
    body.innerHTML = `<div class="error-panel">Failed to load: ${escHtml(e.message)}</div>`;
  }
};

function buildSidePanelContent(w, rid, isLastInGroup) {
  const wid = String(w.warning_id || "");
  const ruleId = formatRuleId(w.rule_id || w.guideline_id || w.misra_rule || "");
  const msg = w.message || w.warning_message || "";
  const fp = w.file_path ? w.file_path.replace(/\\\\/g, "/").split("/").pop() : "";
  const fixes = w.fix_suggestions || w.ranked_fixes || w.fixes || [];
  const expl = w.explanation || {};
  const risk = w.risk_analysis || {};
  const dev = w.deviation_advice || {};

  const sc = w.source_context || w._source_context || "";
  const srcTxt = typeof sc === "string" ? sc
    : (sc && sc.context_text) ? sc.context_text
      : Array.isArray(sc) ? sc.join("\n") : "";

  window._fixData = window._fixData || {};
  window._fixData[wid] = { fixes, beforeCode: srcTxt, selectedIdx: 0, rid };

  let html = "";

  html += `<div class="sp-meta-row">
    ${ruleId ? `<span class="w-rule-pill">Rule ${escHtml(ruleId)}</span>` : ""}
    ${fp ? `<span class="sp-file-tag">&#128196; ${escHtml(fp)}</span>` : ""}
    ${w.guideline_title ? `<span class="sp-guideline">${escHtml(w.guideline_title)}</span>` : ""}
  </div>`;
  if (msg) html += `<div class="sp-msg">${escHtml(msg)}</div>`;

  /* ── Determine which line is violated (hoisted so both code blocks can use it) ──
     Strategy 1: >>> marker on the line
     Strategy 2: line_start field if populated
     Strategy 3: fuzzy-match fix's patched_code identifiers against source lines */
  const _ls = parseInt(w.line_start || 0);
  const _le = parseInt(w.line_end || _ls);
  let _fuzzyViolatedLine = 0;

  if (srcTxt) {
    /* Strategy 3 prep: extract tokens from the first fix suggestion */
    if (!_ls && fixes.length) {
      const _pc = (fixes[0].patched_code || fixes[0].corrected_code || fixes[0].fixed_code || "");
      /* Extract the "after" code if it contains BEFORE:/AFTER: */
      let _afterCode = _pc;
      const _afIdx = _pc.toUpperCase().indexOf("AFTER:");
      if (_afIdx !== -1) _afterCode = _pc.slice(_afIdx + 6).trim();
      /* Clean prose "replace X with Y" */
      const _wIdx = _afterCode.search(/\bwith\s/i);
      if (_wIdx !== -1) _afterCode = _afterCode.slice(_wIdx + 5).trim();
      /* Extract meaningful identifiers (skip common C keywords) */
      const _cKw = new Set(["int", "uint8_t", "uint16_t", "uint32_t", "char", "void", "return",
        "if", "else", "for", "while", "static", "const", "replace", "with", "printf", "fprintf", "NULL"]);
      const _patchToks = [...new Set((_afterCode.match(/[a-zA-Z_][a-zA-Z0-9_]*/g) || [])
        .filter(t => !_cKw.has(t)))];
      /* Score each source line */
      if (_patchToks.length) {
        const _srcLines = srcTxt.split("\n");
        const _DECL = /^\s*[a-zA-Z_]\w*(?:\s*\*)?\s+[a-zA-Z_]\w*\s*(?:=|;)/;
        const _ASGN = /^\s*[a-zA-Z_]\w*\s*(?:\[.*?\])?\s*=/;
        const _kind = s => { s = s.trim(); if (_DECL.test(s)) return "d"; if (_ASGN.test(s)) return "a"; return "o"; };
        const _pKind = _kind(_afterCode);
        let _bestScore = 0, _bestLine = 0;
        _srcLines.forEach(ln => {
          const mc = ln.replace(/^\s*>>>/, "   ").match(/^\s*(\d+)\s+(.*)/);
          if (!mc) return;
          const lnum = parseInt(mc[1]);
          const lcode = mc[2];
          const lToks = new Set((lcode.match(/[a-zA-Z_][a-zA-Z0-9_]*/g) || []));
          const score = _patchToks.filter(t => lToks.has(t)).length
            + (_kind(lcode) === _pKind ? 2 : 0);
          if (score > _bestScore) { _bestScore = score; _bestLine = lnum; }
        });
        if (_bestScore > 0) _fuzzyViolatedLine = _bestLine;
      }
    }

    const rows = srcTxt.split("\n").map(ln => {
      const clean = ln.replace(/^\s*>>>/, "   ");
      const m = clean.match(/^\s*(\d+)\s+(.*)/);
      if (!m) return clean.trim() ? `<div class="code-row"><span class="ln-num"></span><span class="ln-code">${escHtml(clean.trimEnd())}</span></div>` : null;
      const isFlagged = ln.includes(">>>");
      const lineNum = parseInt(m[1]);
      const isViolated = isFlagged
        || (lineNum > 0 && _ls > 0 && lineNum >= _ls && lineNum <= _le)
        || (lineNum > 0 && _fuzzyViolatedLine > 0 && lineNum === _fuzzyViolatedLine);
      return `<div class="code-row${isViolated ? " flagged violated-line" : ""}"><span class="ln-num">${escHtml(m[1])}</span><span class="ln-code">${escHtml(m[2].trimEnd())}</span></div>`;
    }).filter(Boolean).join("");
    if (rows) html += `
      <div class="sp-section">
        <div class="sp-section-title">&#128196; Violated Source Code <span class="violated-legend">&#128308; = violated line</span></div>
        <div class="source-block before-block" style="border-radius:var(--r);border:1px solid rgba(192,57,43,.2);">${rows}</div>
      </div>`;
  }

  if (expl.summary || expl.rule_basis || expl.code_evidence) {
    html += `<div class="sp-section">
      <div class="sp-section-title">&#128221; Explanation</div>
      ${expl.summary ? `<div class="sp-field"><span class="sp-label">Summary</span><span class="sp-value">${escHtml(expl.summary)}</span></div>` : ""}
      ${expl.rule_basis ? `<div class="sp-field"><span class="sp-label">Rule Basis</span><span class="sp-value">${escHtml(expl.rule_basis)}</span></div>` : ""}
      ${expl.code_evidence ? `<div class="sp-field"><span class="sp-label">Code Evidence</span><span class="sp-value">${escHtml(expl.code_evidence)}</span></div>` : ""}
    </div>`;
  }

  const failures = Array.isArray(risk.potential_failures) && risk.potential_failures.length
    ? risk.potential_failures : [];
  if (risk.why || failures.length || risk.runtime_risk) {
    const failList = failures.length
      ? `<ul class="sp-list">${failures.map(f => `<li>${escHtml(f)}</li>`).join("")}</ul>` : "";
    html += `<div class="sp-section">
      <div class="sp-section-title">&#9888;&#65039; Risk if Not Fixed</div>
      ${risk.why ? `<div class="sp-field"><span class="sp-label">Impact</span><span class="sp-value">${escHtml(risk.why)}</span></div>` : ""}
      ${failList ? `<div class="sp-field"><span class="sp-label">Potential Failures</span><span class="sp-value">${failList}</span></div>` : ""}
      ${risk.runtime_risk ? `<div class="sp-field"><span class="sp-label">Runtime Risk</span><span class="sp-value">${escHtml(risk.runtime_risk)}</span></div>` : ""}
    </div>`;
  }

  if (dev.deviation_possible || dev.recommended_decision) {
    const devClass = { Yes: "dev-yes", No: "dev-no", Conditional: "dev-cond" }[dev.deviation_possible] || "dev-unknown";
    html += `<div class="sp-section">
      <div class="sp-section-title">&#128260; Deviation Advice</div>
      <div class="sp-field"><span class="sp-label">Deviation Possible</span><span class="sp-value"><span class="dev-badge ${devClass}">${escHtml(dev.deviation_possible || "Unknown")}</span></span></div>
      ${dev.recommended_decision ? `<div class="sp-field"><span class="sp-label">Decision</span><span class="sp-value">${escHtml(dev.recommended_decision)}</span></div>` : ""}
      ${dev.required_justification ? `<div class="sp-field"><span class="sp-label">Justification</span><span class="sp-value">${escHtml(dev.required_justification)}</span></div>` : ""}
      ${dev.review_notes ? `<div class="sp-field"><span class="sp-label">Review Notes</span><span class="sp-value">${escHtml(dev.review_notes)}</span></div>` : ""}
    </div>`;
  }

  if (fixes.length) {
    const chips = fixes.map((f, i) =>
      `<button class="fix-chip ${i === 0 ? "fix-chip-active" : ""}" id="fixchip-${escHtml(wid)}-${i}"
        onclick="selectFixChip('${escHtml(wid)}',${i})"
      >Fix ${i + 1}</button>`
    ).join("");

    const firstFix = fixes[0];
    const afterCode = extractAfterCode(firstFix);

    /* Fuzzy match fallback for before-block: reuse _ls/_le/_fuzzyViolatedLine hoisted above */
    const beforeRows = srcTxt
      ? srcTxt.split("\n").map(ln => {
        const clean = ln.replace(/^\s*>>>/, "   ");
        const m = clean.match(/^\s*(\d+)\s+(.*)/);
        const isFlagged = ln.includes(">>>");
        const lineNum = m ? parseInt(m[1]) : 0;
        /* Highlight: >>> marker, line_start..line_end range, OR fuzzy match */
        const isViolated = isFlagged
          || (lineNum > 0 && _ls > 0 && lineNum >= _ls && lineNum <= _le)
          || (lineNum > 0 && _fuzzyViolatedLine > 0 && lineNum === _fuzzyViolatedLine);
        return m
          ? `<div class="code-row${isViolated ? " flagged violated-line" : ""}"><span class="ln-num">${escHtml(m[1])}</span><span class="ln-code">${escHtml(m[2].trimEnd())}</span></div>`
          : (clean.trim() ? `<div class="code-row"><span class="ln-num"></span><span class="ln-code">${escHtml(clean.trimEnd())}</span></div>` : "");
      }).join("")
      : '<div class="sp-no-src">Source not available</div>';

    html += `<div class="sp-section sp-fixes-section">
      <div class="sp-section-title">&#128295; Fix Suggestions <span class="fix-count-tag">${fixes.length} option${fixes.length > 1 ? "s" : ""}</span></div>
      <div class="fix-chips-row">${chips}</div>
      <div class="fix-title-row" id="fix-title-${escHtml(wid)}">${escHtml(firstFix.title || "")}</div>
      <div id="fix-review-warn-${escHtml(wid)}">${firstFix.needs_review ? `<div class="fix-review-warning"><span class="fix-review-warning-icon">&#9888;</span><div><strong>Needs manual review</strong><ul>${(firstFix.validator_warnings || []).map(w => `<li>${escHtml(w)}</li>`).join("")}</ul></div></div>` : ""}</div>
      <div class="fix-why-row"   id="fix-why-${escHtml(wid)}">${escHtml(firstFix.why || "")}</div>

      <div class="fix-diff-wrap">
        <div class="fix-diff-col">
          <div class="fix-diff-header before-header">&#128308; BEFORE (VIOLATED CODE)</div>
          <div class="source-block before-block" id="before-block-${escHtml(wid)}">${beforeRows}</div>
        </div>
        <div class="fix-diff-col">
          <div class="fix-diff-header after-header" style="display:flex;align-items:center;justify-content:space-between;">
            <span>&#128994; AFTER (FIXED CODE)</span>
            <button class="sp-edit-btn" id="sp-edit-btn-${escHtml(wid)}" onclick="toggleFixEdit('${escHtml(wid)}')" title="Edit the suggested fix code manually">&#9998; Edit</button>
          </div>
          <div class="source-block after-block" id="after-block-${escHtml(wid)}">
            <div id="after-code-${escHtml(wid)}">${renderAfterCode(afterCode)}</div>
            <textarea id="after-edit-area-${escHtml(wid)}" class="fix-edit-area hidden" spellcheck="false"></textarea>
          </div>
          <div class="sp-commit-row" style="display:flex;align-items:center;gap:8px;margin-top:6px;flex-wrap:wrap;">
            <button class="commit-btn-inline" id="commit-btn-${escHtml(wid)}" onclick="commitFix('${escHtml(wid)}')"
              title="Saves the selected fix into the original source file and logs it to the audit report">
              &#x2B06; Commit Fix to File
              <span class="info-tip" title="Saves the selected fix into the original source file and logs it to the audit report">&#9432;</span>
            </button>
            <button class="go-without-btn" id="go-without-btn-${escHtml(wid)}" onclick="goWithoutChange('${escHtml(wid)}')"
              title="Mark this warning as reviewed but keep the original code unchanged">
              &#128683; Go Without Change
            </button>
          </div>
        </div>
      </div>

      ${firstFix.compliance_notes ? `<div class="fix-notes-row" id="fix-notes-${escHtml(wid)}"><strong>Compliance:</strong> ${escHtml(firstFix.compliance_notes)}</div>` : `<div class="fix-notes-row" id="fix-notes-${escHtml(wid)}"></div>`}

      <div class="patched-file-wrap hidden" id="patched-wrap-${escHtml(wid)}">
        <div class="patched-file-header">
          <span class="patched-file-title" id="patched-file-title-${escHtml(wid)}">&#x2713; Patched File</span>
          <a class="btn-download" id="download-link-${escHtml(wid)}" href="#" download>&#x2B07; Download</a>
        </div>
        <div class="source-block patched-full-block" id="patched-code-${escHtml(wid)}"></div>
      </div>
    </div>`;
  } else {
    html += `<div class="sp-section">
      <div class="sp-section-title">&#128295; Fix Suggestions</div>
      <div class="sp-no-fixes">No fix suggestions could be generated for this warning.${w.parse_error ? " <em>(Parse error — try re-running.)</em>" : ""}</div>
    </div>`;
  }

  /* BUG 2 FIX: Link to merged report containing ALL completed runs, not just this one.
     Collect all run IDs from misra_completed_runs in sessionStorage. */
  var _allRunIds = [rid];
  try {
    var _crs = JSON.parse(sessionStorage.getItem("misra_completed_runs") || "[]");
    _crs.forEach(function (r) { if (r.runId && r.runId !== rid) _allRunIds.push(r.runId); });
  } catch (_e) { }
  var _mergedRid = _allRunIds.length > 1 ? "merged/" + _allRunIds.join(",") : rid;
  /* FEATURE 2: Show View Full Report only on last record of the file group */
  if (isLastInGroup !== false) {
    html += `<div class="sp-full-link"><a href="/results/${escHtml(_mergedRid)}" class="btn btn-primary btn-sm">View Full Report &#8594;</a></div>`;
  }
  return html;
}



/* ============================================================
   RESULTS PAGE
   ============================================================ */
/* Global fallback: _rrRenderAfterBlock is set inside initResultsPage,
   but buildWarningDetail (outside) calls it via window._rrRenderAfterBlock */
window._rrRenderAfterBlock = function (wId, fallbackAfterCode) {
  var committed = (window._commitResults || {})[wId];
  if (committed && committed.patchedCode) {
    var pStart = committed.patchLineStart || 0;
    var pEnd = pStart ? pStart + (committed.patchLineCount || 0) - 1 : 0;
    return committed.patchedCode.split("\n").map(function (ln, i) {
      var num = i + 1, isChg = pStart > 0 && num >= pStart && num <= pEnd;
      return '<div class="code-row' + (isChg ? ' patch-highlight' : '') + '">'
        + '<span class="ln-num">' + num + '</span>'
        + '<span class="ln-code">' + escHtml(ln) + '</span></div>';
    }).join("");
  }
  /* FIX 5: No action taken yet — return empty; buildWarningDetail handles pending state */
  return "";
};

function initResultsPage() {
  const root = document.getElementById("results-root");
  const runId = window.MISRA_RUN_ID;
  let allWarnings = [];

  /* CRITICAL: Restore _noChangeResults and _commitResults (metadata only, no patchedCode yet)
     from sessionStorage SYNCHRONOUSLY before any rendering happens.
     buildWarningDetail() reads these to decide AWAITING / NO-CHANGE / COMMITTED state.
     Without this, every card renders as AWAITING DECISION on page load/navigation. */
  (function _restoreActionStatesEarly() {
    try {
      var _nc = JSON.parse(sessionStorage.getItem("misra_no_change") || "{}");
      if (Object.keys(_nc).length) {
        window._noChangeResults = window._noChangeResults || {};
        Object.keys(_nc).forEach(function (wid) { window._noChangeResults[wid] = true; });
      }
    } catch (_e) { }
    try {
      var _cm = JSON.parse(sessionStorage.getItem("misra_commits") || "{}");
      if (Object.keys(_cm).length) {
        window._commitResults = window._commitResults || {};
        Object.keys(_cm).forEach(function (wid) {
          /* Only seed if not already populated (same-session commit already has full data) */
          if (!window._commitResults[wid]) {
            var m = _cm[wid];
            window._commitResults[wid] = {
              afterCode: "",          /* fetched lazily by _restoreCommittedPatches */
              patchedCode: "",        /* fetched lazily */
              patchLineStart: m.patchLineStart || 0,
              patchLineCount: m.patchLineCount || 0,
              originalFile: m.originalFile || "",
              downloadUrl: m.downloadUrl || "",
              filename: m.filename || "patched.c",
              isFullFile: m.isFullFile || false,
              wasUserEdited: m.wasUserEdited || false,
              _needsServerLoad: true
            };
          }
        });
      }
    } catch (_e) { }
  })();

  loadResult();

  async function loadResult() {
    try {
      /* BUG 2 FIX: Support merged run IDs ("merged/runA,runB") so Review Report
         shows ALL warnings from all per-file runs — /api/result/merged/<ids> handles it. */
      const r = await fetch(`/api/result/${runId}`);
      const data = await r.json();
      if (!r.ok || data.error) { root.innerHTML = `<div class="error-panel">${escHtml(data.error || "Failed to load")}</div>`; return; }
      allWarnings = data.warnings || [];
      root.innerHTML = buildShell(data);
      if (!allWarnings.length) {
        document.getElementById("warning-list").innerHTML = `<div style="text-align:center;padding:60px 20px;"><div style="font-size:36px;margin-bottom:12px;">&#x2139;&#xFE0F;</div><div style="font-family:var(--font-display);font-size:17px;font-weight:600;color:var(--text);margin-bottom:8px;">No warnings to show</div><a href="/" class="btn btn-primary" style="margin-top:16px;">&#x2190; New Review</a></div>`;
        return;
      }
      renderWarnings(allWarnings);
      attachFilterHandlers();
      // Add Save to Audit Excel button at the bottom of the Review Report page
      _addSaveAllAuditBtn();
      // Auto-load committed patches so "AFTER" block shows full patched file
      _restoreCommittedPatches(allWarnings);
    } catch (err) { root.innerHTML = `<div class="error-panel">Failed to load: ${escHtml(err.message)}</div>`; }
  }


  function buildShell(data) {
    const s = data.summary || {};
    const total = s.total ?? (data.warnings || []).length;
    const manual = s.manual ?? 0;
    return `
    <div style="padding:40px 0 28px;border-bottom:1px solid var(--border);margin-bottom:28px;">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap;">
        <button class="btn btn-ghost btn-sm results-back-btn"
           onclick="window.location.href='/'"
           style="display:inline-flex;align-items:center;gap:6px;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          ← Back
        </button>
        <button class="btn btn-ghost btn-sm" onclick="confirmNewAnalysis()"
          style="display:inline-flex;align-items:center;gap:6px;">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
          Run New Analysis
        </button>
      </div>
      <h1 style="font-family:var(--font-display);font-size:clamp(22px,3vw,34px);font-weight:700;letter-spacing:-.015em;margin-bottom:8px;">Review Report</h1>
      <p style="color:var(--text-sub);font-size:14px;">${total} warning${total !== 1 ? "s" : ""} reviewed</p>
    </div>
    <div class="stat-grid" style="grid-template-columns:repeat(2,1fr);max-width:360px;margin-bottom:28px;">
      <div class="stat-tile s-total"><div class="stat-number">${total}</div><div class="stat-label">Total</div></div>
      <div class="stat-tile s-review"><div class="stat-number">${manual}</div><div class="stat-label">Needs Review</div></div>
    </div>
    <div class="filter-row" id="filter-bar">
      <span class="filter-label-text">Rule type</span>
      <button class="filter-btn active" data-misra="all">All</button>
      <button class="filter-btn" data-misra="advisory">Advisory</button>
      <button class="filter-btn" data-misra="required">Required</button>
      <button class="filter-btn" data-misra="mandatory">Mandatory</button>
    </div>
    <div class="warning-list" id="warning-list"></div>`;
  }

  /* ── _rrRenderAfterBlock: show full patched code if committed, else fix snippet ── */
  window._rrRenderAfterBlock = function _rrRenderAfterBlock(wId, fallbackAfterCode) {
    var committed = (window._commitResults || {})[wId];
    if (committed && committed.patchedCode) {
      var pStart = committed.patchLineStart || 0;
      var pEnd = pStart ? pStart + (committed.patchLineCount || 0) - 1 : 0;
      return committed.patchedCode.split("\n").map(function (ln, i) {
        var num = i + 1, isChg = pStart > 0 && num >= pStart && num <= pEnd;
        return '<div class="code-row' + (isChg ? ' patch-highlight' : '') + '">'
          + '<span class="ln-num">' + num + '</span>'
          + '<span class="ln-code">' + escHtml(ln) + '</span></div>';
      }).join("");
    }
    return renderAfterCode(fallbackAfterCode);
  }

  /* ── _addSaveAllAuditBtn: single Save to Audit Excel button at bottom of page ── */
  function _addSaveAllAuditBtn() {
    var root = document.getElementById("results-root");
    if (!root) return;
    var existing = document.getElementById("rr-save-all-wrap");
    if (existing) existing.remove();
    var wrap = document.createElement("div");
    wrap.id = "rr-save-all-wrap";
    wrap.style.cssText = "margin-top:32px;padding:24px;border-top:1px solid var(--border);display:flex;align-items:center;gap:16px;flex-wrap:wrap;";
    wrap.innerHTML = '<button id="rr-save-all-btn" onclick="rrSaveAllAudit()"'
      + ' style="background:#1e40af;color:#fff;border:none;padding:9px 24px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;gap:8px;">'
      + '&#128190; Save All to Audit Excel'
      + '</button>'
      + '<span id="rr-save-all-status" style="font-size:13px;color:var(--text-muted);"></span>';
    root.appendChild(wrap);
  }

  /* ── rrSaveAllAudit: save all reviewed warnings to audit in one click ── */
  window.rrSaveAllAudit = async function () {
    var btn = document.getElementById("rr-save-all-btn");
    var statusEl = document.getElementById("rr-save-all-status");
    if (btn) { btn.disabled = true; btn.textContent = "Saving…"; }
    var fixData = window._fixData || {};
    var commitResults = window._commitResults || {};
    var noChangeResults = window._noChangeResults || {};
    var wIds = Object.keys(fixData);
    if (!wIds.length) {
      if (statusEl) { statusEl.style.color = "#dc2626"; statusEl.textContent = "⚠ No warnings to save. Run analysis first."; }
      if (btn) { btn.disabled = false; btn.innerHTML = "&#128190; Save All to Audit Excel"; }
      return;
    }
    var saved = 0, failed = 0;
    for (var i = 0; i < wIds.length; i++) {
      var wId = wIds[i];
      var committed = commitResults[wId];
      var fd = fixData[wId];
      var isNoChange = !!noChangeResults[wId];
      var runId = committed ? committed.runId : (fd ? (fd.rid || "") : "");

      /* Build all fix suggestions */
      var allFixes = [];
      if (fd && fd.fixes) {
        fd.fixes.forEach(function (f, idx) {
          allFixes.push({ index: idx + 1, title: f.title || f.fix_title || ("Fix " + (idx + 1)), code: extractAfterCode(f) });
        });
      }

      /* Determine chosen fix and user-edit state */
      var chosenFixIndex = null, chosenFixCode = "", userEditedCode = "", fixedCodeFull = "";
      if (committed) {
        fixedCodeFull = committed.patchedCode || committed.afterCode || "";
        if (committed.wasUserEdited) {
          userEditedCode = committed.afterCode || "";
        } else {
          var selIdx = fd ? (fd.selectedIdx || 0) : 0;
          chosenFixIndex = selIdx + 1;
          chosenFixCode = allFixes[selIdx] ? allFixes[selIdx].code : "";
        }
      }

      var payload = {
        warning_id: wId, run_id: runId,
        all_fixes: allFixes,
        chosen_fix_index: chosenFixIndex, chosen_fix_code: chosenFixCode,
        fixed_code_full: fixedCodeFull,
        user_edited_code: userEditedCode,
        is_no_change: isNoChange,
        was_user_edited: !!(committed && committed.wasUserEdited)
      };
      try {
        var r = await fetch("/api/save_audit", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        var res = await r.json();
        if (res.status === "ok") saved++; else failed++;
      } catch (e) { failed++; }
    }
    if (statusEl) {
      if (saved > 0) {
        statusEl.style.color = "#065f46";
        statusEl.textContent = "✓ " + saved + " warning" + (saved !== 1 ? "s" : "") + " saved to audit Excel" + (failed > 0 ? " (" + failed + " failed)" : "");
      } else {
        statusEl.style.color = "#dc2626";
        statusEl.textContent = "⚠ No warnings saved" + (failed > 0 ? " — " + failed + " errors" : "");
      }
    }
    if (btn) {
      btn.textContent = saved > 0 ? "✓ Saved" : "&#128190; Save All to Audit Excel";
      if (saved > 0) btn.style.background = "#15803d";
      else btn.disabled = false;
    }
  };

  /* Back button — just navigate, no confirmation needed (report stays at its URL) */
  window.confirmLeave = function () {
    return true;  // no confirmation — report is safely saved on server
  };

  /* ── Auto-restore committed patches from server on page load ── */
  async function _restoreCommittedPatches(warnings) {
    window._commitResults = window._commitResults || {};
    var _storedMeta = {};
    try { _storedMeta = JSON.parse(sessionStorage.getItem("misra_commits") || "{}"); } catch (_e) { }

    for (const w of warnings) {
      const wId = String(w.warning_id || "");
      if (!wId) continue;
      // Only restore if user actually committed this wid this session
      const meta = _storedMeta[wId];
      if (!meta) continue;  // not committed — skip entirely
      // Skip if already fully loaded (same-session commit via side panel has patchedCode)
      if (window._commitResults[wId] && window._commitResults[wId].patchedCode && !window._commitResults[wId]._needsServerLoad) continue;
      try {
        const r = await fetch("/api/committed/" + encodeURIComponent(wId));
        if (!r.ok) continue;
        const data = await r.json();
        if (!data.committed || !data.patched_code) continue;
        window._commitResults[wId] = {
          afterCode: data.patched_code,
          runId: runId,
          patchedCode: data.patched_code,
          patchLineStart: meta.patchLineStart || 0,
          patchLineCount: meta.patchLineCount || 0,
          originalFile: meta.originalFile || data.original_file || "",
          downloadUrl: meta.downloadUrl || data.download_url || "",
          filename: meta.filename || data.filename || "patched.c",
          isFullFile: true,
          wasUserEdited: meta.wasUserEdited || false,
          _needsServerLoad: false
        };
        // Live-update the already-rendered card's AFTER block with real patched code
        _rrRefreshAfterBlock(wId);
      } catch (_e) { /* best-effort */ }
    }
  }

  /* Run New Analysis confirmation */
  window.confirmNewAnalysis = function () {
    const ok = confirm(
      "Start a fresh analysis?\n\n" +
      "This will take you back to the Upload page to start from scratch. " +
      "Your current report will remain saved on the server.\n\nContinue?"
    );
    if (ok) window.location.href = "/";
  };

  function renderWarnings(ws) {
    const list = document.getElementById("warning-list");
    if (!list) return;
    list.innerHTML = ws.map((w, i) => buildWarningCard(w, i)).join("");
  }

  function attachFilterHandlers() {
    const savedFilter = sessionStorage.getItem("misra_filter");
    let activeMisra = savedFilter || "all";
    if (savedFilter) sessionStorage.removeItem("misra_filter");

    function applyFilters() {
      document.querySelectorAll(".warning-card").forEach(card => {
        const misraOk = activeMisra === "all" || card.dataset.misra === activeMisra;
        card.style.display = misraOk ? "" : "none";
      });
    }

    document.querySelectorAll(".filter-btn[data-misra]").forEach(btn => {
      if (btn.dataset.misra === activeMisra) { document.querySelectorAll(".filter-btn[data-misra]").forEach(b => b.classList.remove("active")); btn.classList.add("active"); }
      btn.addEventListener("click", () => {
        document.querySelectorAll(".filter-btn[data-misra]").forEach(b => b.classList.remove("active"));
        btn.classList.add("active"); activeMisra = btn.dataset.misra; applyFilters();
      });
    });
    applyFilters();
  }
}

/* ============================================================
   BUILD WARNING CARD
   ============================================================ */
function buildWarningCard(w, idx) {
  const ev = w.evaluation || w.evaluator_result || {};
  const isReview = !!(ev.manual_review_required || ev.flag_for_review || ev.needs_manual_review);
  const wId = w.warning_id || `W${idx + 1}`;
  const ruleId = w.rule_id || w.misra_rule || "";
  const msg = w.message || w.warning_message || "";
  const loc = w.file_path ? baseName(w.file_path) : "";
  const sev = (w.severity || "").toLowerCase();
  const misraCat = deriveMisraCategory(w);

  return `<div class="warning-card ${isReview ? "review-flag" : ""}"
    data-review="${isReview}" data-id="${escHtml(wId)}" data-misra="${escHtml(misraCat)}"
    style="animation-delay:${Math.min(idx * 0.035, 0.5)}s">
    <div class="warning-header" onclick="toggleCard('${escHtml(wId)}')" >
      <span class="w-id">${escHtml(wId)}</span>
      ${ruleId ? `<span class="w-rule-pill">Rule ${escHtml(formatRuleId(ruleId))}</span>` : ""}
      <span class="w-msg">${escHtml(msg)}</span>
      ${loc ? `<span class="w-loc">${escHtml(loc)}</span>` : ""}
      ${isReview ? "<span class=\"conf-badge review\">Needs Review</span>" : ""}
      <svg class="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
    </div>
    <div class="warning-detail">${buildWarningDetail(w, ev, isReview, wId)}</div>
  </div>`;
}

function deriveMisraCategory(w) {
  /* Check rule_type first */
  const rt = (w.rule_type || "").toLowerCase();
  if (rt === "mandatory") return "mandatory";
  if (rt === "required") return "required";
  if (rt === "advisory") return "advisory";

  /* "category" field from enriched: "MISRA-R (Required)", "MISRA-M (Mandatory)", "MISRA-A (Advisory)" */
  const cat = (w.category || w.rule_category || w.misra_category || "").toLowerCase();
  if (cat.includes("mandatory") || cat.includes("misra-m")) return "mandatory";
  if (cat.includes("required") || cat.includes("misra-r")) return "required";
  if (cat.includes("advisory") || cat.includes("misra-a")) return "advisory";

  /* Derive from rule_id using MISRA-C 2012 classification */
  const rid = (w.rule_id || w.guideline_id || "").toLowerCase().replace(/^rule[\s\-_]*/i, "");
  /* Mandatory rules: 9.1, 12.5, 13.6, 17.3, 17.4, 17.6, 19.1, 21.13, 21.17-21.20, 22.5 */
  const mandatoryRules = new Set(["9.1", "12.5", "13.6", "17.3", "17.4", "17.6", "19.1", "21.13", "21.17", "21.18", "21.19", "21.20", "22.5"]);
  /* Advisory rules: 1.2, 2.3, 2.4, 2.5, 2.6, 2.7, 4.2, 5.9, 8.7, 8.9, 8.11, 8.13, 10.5, 11.4, 11.5, 12.1, 12.3, 12.4, 13.3, 13.4, 15.1, 15.4, 15.5, 17.5, 17.8, 18.4, 18.5, 19.2, 20.1, 20.5, 20.10, 21.12 */
  const advisoryRules = new Set(["1.2", "2.3", "2.4", "2.5", "2.6", "2.7", "4.2", "5.9", "8.7", "8.9", "8.11", "8.13", "10.5", "11.4", "11.5", "12.1", "12.3", "12.4", "13.3", "13.4", "15.1", "15.4", "15.5", "17.5", "17.8", "18.4", "18.5", "19.2", "20.1", "20.5", "20.10", "21.12"]);
  if (mandatoryRules.has(rid)) return "mandatory";
  if (advisoryRules.has(rid)) return "advisory";
  if (rid) return "required";   /* everything else in MISRA-C 2012 is Required */

  /* Fallback: scan misra_context chunks */
  const ctx = w.misra_context || w.retrieved_context || [];
  if (Array.isArray(ctx)) {
    for (const chunk of ctx) {
      const g = (chunk.guidelines || chunk.description || chunk.body_text || "").toLowerCase();
      if (g.includes("(mandatory)") || g.includes("misra-m")) return "mandatory";
      if (g.includes("(required)") || g.includes("misra-r")) return "required";
      if (g.includes("(advisory)") || g.includes("misra-a")) return "advisory";
    }
  }
  return "";
}

function buildWarningDetail(w, ev, isReview, wId) {
  let html = "";
  if (isReview) html += `<div class="review-banner mt-16"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg> Flagged for manual review.</div>`;

  const SKIP = new Set(["source_context", "source_lines", "misra_context", "retrieved_context", "line_start", "line_end", "_excel_row", "_source_context", "_from_cache", "evaluation", "evaluator_result", "ranked_fixes", "fix_suggestions", "fixes"]);
  const row = w._excel_row || {};
  const rowKeys = Object.keys(row).filter(k => !SKIP.has(k) && row[k] && String(row[k]).trim());
  if (rowKeys.length) html += `<div class="detail-section"><div class="detail-section-title">Warning Details</div><table class="excel-table">${rowKeys.map(k => `<tr><td>${escHtml(friendlyKey(k))}</td><td>${escHtml(String(row[k]))}</td></tr>`).join("")}</table></div>`;

  const srcCtxRaw = w._source_context || w.source_context || w.source_code || "";
  let sourceCode = "";
  if (typeof srcCtxRaw === "string") sourceCode = srcCtxRaw;
  else if (Array.isArray(srcCtxRaw)) sourceCode = srcCtxRaw.join("\n");
  else if (srcCtxRaw && typeof srcCtxRaw === "object") sourceCode = srcCtxRaw.context_text || srcCtxRaw.code || srcCtxRaw.text || srcCtxRaw.content || srcCtxRaw.source || "";

  // ── Violated line detection (same 3-strategy as side panel) ──
  const _rpLs = parseInt(w.line_start || 0), _rpLe = parseInt(w.line_end || (w.line_start || 0));
  let _rpFuzzy = 0;
  (function () {
    const _fx0 = w.ranked_fixes || w.fix_suggestions || w.fixes || [];
    if (_rpLs || !_fx0.length || !sourceCode) return;
    let _af = (_fx0[0].patched_code || _fx0[0].corrected_code || _fx0[0].fixed_code || "");
    const _ai = _af.toUpperCase().indexOf("AFTER:"); if (_ai !== -1) _af = _af.slice(_ai + 6).trim();
    const _wi = _af.search(/\bwith\s/i); if (_wi !== -1) _af = _af.slice(_wi + 5).trim();
    const _kw = new Set(["int", "uint8_t", "uint16_t", "uint32_t", "char", "void", "return", "if", "else", "for", "while", "static", "const", "replace", "with", "printf", "fprintf", "NULL"]);
    const _pt = [...new Set((_af.match(/[a-zA-Z_][a-zA-Z0-9_]*/g) || []).filter(t => !_kw.has(t)))];
    if (!_pt.length) return;
    const _D = /^\s*[a-zA-Z_]\w*(?:\s*\*)?\s+[a-zA-Z_]\w*\s*(?:=|;)/, _A = /^\s*[a-zA-Z_]\w*\s*(?:\[.*?\])?\s*=/;
    const _k = s => { s = s.trim(); if (_D.test(s)) return "d"; if (_A.test(s)) return "a"; return "o"; };
    const _pk = _k(_af); let _bs = 0, _bl = 0;
    sourceCode.split("\n").forEach(ln => {
      const mc = ln.replace(/^\s*>>>/, "   ").match(/^\s*(\d+)\s+(.*)/);
      if (!mc) return;
      const lnum = parseInt(mc[1]), lcode = mc[2];
      const lt = new Set((lcode.match(/[a-zA-Z_][a-zA-Z0-9_]*/g) || []));
      const sc = _pt.filter(t => lt.has(t)).length + (_k(lcode) === _pk ? 2 : 0);
      if (sc > _bs) { _bs = sc; _bl = lnum; }
    });
    if (_bs > 0) _rpFuzzy = _bl;
  })();

  // Helper: build BEFORE rows with red violated-line highlight
  function _rpBefore(src) {
    if (!src) return '<div style="padding:10px;color:var(--text-muted);font-size:12px;">Source not available</div>';
    return src.split("\n").map(ln => {
      const clean = ln.replace(/^\s*>>>/, "   ");
      const m = clean.match(/^\s*(\d+)\s+(.*)/);
      if (!m) return clean.trim() ? `<div class="code-row"><span class="ln-num"></span><span class="ln-code">${escHtml(clean.trimEnd())}</span></div>` : null;
      const flagged = ln.includes(">>>");
      const lnum = parseInt(m[1]);
      const viol = flagged || (lnum > 0 && _rpLs > 0 && lnum >= _rpLs && lnum <= _rpLe) || (lnum > 0 && _rpFuzzy > 0 && lnum === _rpFuzzy);
      return `<div class="code-row${viol ? " flagged violated-line" : ""}"><span class="ln-num">${escHtml(m[1])}</span><span class="ln-code">${escHtml(m[2].trimEnd())}</span></div>`;
    }).filter(Boolean).join("") || '<div style="padding:10px;color:var(--text-muted);">No lines</div>';
  }


  const expl = w.explanation || ev.explanation || "";
  if (expl) {
    let explHtml = "";
    if (typeof expl === "string") explHtml = escHtml(expl);
    else if (typeof expl === "object" && expl) {
      if (expl.summary) explHtml += `<div style="margin-bottom:8px;">${escHtml(expl.summary)}</div>`;
      if (expl.rule_basis) explHtml += `<div style="font-size:12px;color:var(--text-muted);margin-bottom:4px;"><strong>Rule basis:</strong> ${escHtml(expl.rule_basis)}</div>`;
      if (expl.code_evidence) explHtml += `<div style="font-size:12px;color:var(--text-muted);"><strong>Evidence:</strong> ${escHtml(expl.code_evidence)}</div>`;
    }
    if (explHtml) html += `<div class="detail-section"><div class="detail-section-title">What's Wrong</div><div class="info-box">${explHtml}</div></div>`;
  }

  const risk = w.risk_analysis || ev.risk_analysis || "";
  if (risk) {
    let riskHtml = "";
    if (typeof risk === "string") riskHtml = escHtml(risk);
    else if (typeof risk === "object" && risk) {
      if (risk.why) riskHtml += `<div style="margin-bottom:8px;">${escHtml(risk.why)}</div>`;
      if (risk.severity) riskHtml += `<div style="font-size:12px;margin-bottom:4px;"><strong>Severity:</strong> <span style="color:var(--red);">${escHtml(risk.severity)}</span></div>`;
      if (Array.isArray(risk.potential_failures) && risk.potential_failures.length)
        riskHtml += `<div style="font-size:12px;color:var(--text-muted);"><strong>Potential failures:</strong> ${risk.potential_failures.map(f => escHtml(f)).join("; ")}</div>`;
    }
    if (riskHtml) html += `<div class="detail-section"><div class="detail-section-title">Why It Matters</div><div class="info-box">${riskHtml}</div></div>`;
  }

  const ruleText = getRuleText(w);
  if (ruleText) html += `<div class="detail-section"><div class="detail-section-title">Rule ${escHtml(formatRuleId(w.rule_id || ""))}</div><div class="info-box">${escHtml(ruleText)}</div></div>`;

  const fixes = w.ranked_fixes || w.fix_suggestions || w.fixes || [];
  if (fixes.length) {
    window._fixData = window._fixData || {};
    /* Use per-warning _run_id (tagged by merged API) so commit uses the correct single run_id */
    window._fixData[wId] = { fixes, beforeCode: sourceCode, selectedIdx: 0, rid: w._run_id || window.MISRA_RUN_ID || "" };

    const firstAfter = extractAfterCode(fixes[0]);
    const chips = fixes.map((f, i) => {
      const isDB = f.source === "db_template" || f.db_verified === true;
      return `<button class="fix-chip ${i === 0 ? "fix-chip-active" : ""}" id="fixchip-${escHtml(wId)}-${i}" onclick="selectFixChip('${escHtml(wId)}',${i})" title="${escHtml(f.title || f.fix_title || "Fix " + (i + 1))}">Fix ${i + 1}${isDB ? '<span class="fix-chip-db">DB</span>' : ""}</button>`;
    }).join("");

    const _beforeHtml = _rpBefore(sourceCode);
    const _hasSource = !!sourceCode;

    /* FIX 5: Check if user has taken an action for this wId */
    const _isCommitted = !!(window._commitResults || {})[wId];
    const _isNoChange = !!(window._noChangeResults || {})[wId];
    const _hasAction = _isCommitted || _isNoChange;

    /* Build the AFTER label */
    let _afterLabelHtml, _afterCodeHtml, _afterBorderColor;
    if (_isNoChange) {
      _afterLabelHtml = `<span style="color:#92400e;">\u26A0 NO CHANGE APPLIED</span> <span style="font-size:10px;font-weight:600;background:rgba(234,179,8,.12);color:#92400e;padding:1px 8px;border-radius:10px;margin-left:4px;">Kept Original</span>`;
      _afterCodeHtml = `<div style="padding:16px 14px;color:var(--text-muted);font-size:13px;font-style:italic;display:flex;align-items:center;gap:8px;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>No fix applied &mdash; original code retained as-is.</div>`;
      _afterBorderColor = 'rgba(234,179,8,.3)';
    } else if (_isCommitted) {
      const _committed = (window._commitResults || {})[wId];
      const _fn = _committed && _committed.originalFile ? ` \u2014 <span style="font-weight:500;opacity:.8;">${escHtml(_committed.originalFile)}</span>` : "";
      const _editLabel = _committed && _committed.wasUserEdited
        ? '<span style="font-size:10px;font-weight:600;background:rgba(37,99,235,.12);color:#1d4ed8;padding:1px 8px;border-radius:10px;margin-left:4px;">&#x270E; User-Edited &amp; Committed</span>'
        : '<span style="font-size:10px;font-weight:600;background:rgba(16,185,129,.12);color:#065f46;padding:1px 8px;border-radius:10px;margin-left:4px;">&#x2713; LLM Fix Committed</span>';
      _afterLabelHtml = `&#128994; AFTER (FULL PATCHED FILE)${_fn} ${_editLabel}`;
      _afterCodeHtml = window._rrRenderAfterBlock(wId, firstAfter);
      _afterBorderColor = 'rgba(21,128,61,.25)';
    } else {
      /* No action taken yet — show pending state */
      const _spRid = w._run_id || window.MISRA_RUN_ID || "";
      _afterLabelHtml = `<span style="color:#92400e;">\u23F3 AWAITING DECISION</span>`;
      _afterCodeHtml = `<div style="padding:20px 16px;display:flex;flex-direction:column;align-items:flex-start;gap:10px;">
        <div style="font-size:13px;color:var(--text-muted);font-style:italic;">No action taken yet for this warning.</div>
        <div style="font-size:12px;color:var(--text-sub);">Open View Results to select a fix or choose to keep the original code.</div>
        <button onclick="window._rrOpenViewResult('${escHtml(wId)}','${escHtml(_spRid)}')"
          style="background:#1e40af;color:#fff;border:none;padding:7px 16px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;gap:6px;">
          &#8594; Open View Results for #${escHtml(wId)}
        </button>
      </div>`;
      _afterBorderColor = 'rgba(234,179,8,.35)';
    }

    html += `<div class="detail-section">
      <div class="detail-section-title">Code Changes</div>
      ${_hasAction ? `<div class="fix-chips-row" id="fixchips-${escHtml(wId)}" style="margin-bottom:12px;">
        ${chips}
        <span class="fix-chip-label" id="fix-chip-desc-${escHtml(wId)}">${escHtml(fixes[0].title || fixes[0].fix_title || fixes[0].why || "")}</span>
      </div>` : ""}
      <div style="display:grid;grid-template-columns:${_hasSource ? "1fr 1fr" : "1fr"};gap:12px;">
        ${_hasSource ? `<div>
          <div style="font-size:11px;font-weight:700;letter-spacing:.05em;color:#c0392b;margin-bottom:6px;">
            &#128308; BEFORE (VIOLATED CODE)
            <span style="font-weight:500;font-size:10px;opacity:.75;"> &#128308; = violated line</span>
          </div>
          <div class="source-block" id="src-${escHtml(wId)}" style="border:1px solid rgba(192,57,43,.25);border-radius:8px;max-height:360px;overflow-y:auto;">${_beforeHtml}</div>
        </div>`: ""}
        <div>
          <div id="rr-after-label-${escHtml(wId)}" style="font-size:11px;font-weight:700;letter-spacing:.05em;color:${_isNoChange ? '#92400e' : (_isCommitted ? '#15803d' : '#92400e')};margin-bottom:6px;">
            ${_afterLabelHtml}
          </div>
          <div class="source-block" id="rr-after-block-${escHtml(wId)}" style="border:1px solid ${_afterBorderColor};border-radius:8px;max-height:360px;overflow-y:auto;">
            <div id="rr-after-code-${escHtml(wId)}">${_afterCodeHtml}</div>
          </div>
          <div id="rr-download-${escHtml(wId)}" style="margin-top:6px;"></div>
        </div>
      </div>
    </div>`;

    const evalNotes = ev.evaluator_notes || ev.notes || ev.summary || "";
    if (evalNotes) html += `<div class="info-box eval-note" style="margin-top:10px;">${escHtml(evalNotes)}</div>`;
  } else {
    html += `<div class="detail-section"><div class="detail-section-title">Fix Suggestion</div><div class="info-box" style="color:var(--text-muted);font-style:italic;">No fix suggestions available for this warning.</div></div>`;
  }

  const devRaw = w.deviation_advice || ev.deviation_advice || "";
  if (devRaw) {
    let devHtml = "";
    if (typeof devRaw === "object" && devRaw) {
      const lm = { deviation_possible: "Deviation possible", recommended_decision: "Recommended action", required_justification: "Justification required", review_notes: "Review notes" };
      devHtml = Object.entries(devRaw).filter(([, v]) => v && String(v).trim()).map(([k, v]) => `<div style="margin-bottom:6px;"><span style="font-weight:600;color:var(--text);">${escHtml(lm[k] || k.replace(/_/g, " "))}: </span><span style="color:var(--text-sub);">${escHtml(String(v))}</span></div>`).join("");
    } else devHtml = escHtml(String(devRaw));
    if (devHtml) html += `<div class="detail-section"><div class="detail-section-title">Exception / Deviation Note</div><div class="info-box deviation">${devHtml}</div></div>`;
  }

  return html || `<div class="text-muted mt-16" style="font-size:12px;">No details available.</div>`;
}

/* FIX 5: Open side panel from Review Report "Open View Results" button.
   On the results page, window.openSidePanel is the same function from module scope. */
window._rrOpenViewResult = function (wid, rid) {
  if (typeof window.openSidePanel === 'function') {
    window._spOpenedFromRR = true;  // flag: opened from Review Report awaiting-decision
    window.openSidePanel(wid, rid);
  }
};

/* ============================================================
   FIX CHIP SELECTOR + COMMIT
   ============================================================ */
window.selectFixChip = function (wId, idx) {
  const data = (window._fixData || {})[wId]; if (!data) return;
  data.selectedIdx = idx;
  /* FEATURE 2: Reset edited code when switching chips */
  delete data._editedCode;
  var editEl2 = document.getElementById("after-edit-area-" + wId);
  var codeEl2 = document.getElementById("after-code-" + wId);
  var editBtn2 = document.getElementById("sp-edit-btn-" + wId);
  if (editEl2 && !editEl2.classList.contains("hidden")) {
    editEl2.classList.add("hidden");
    if (codeEl2) codeEl2.classList.remove("hidden");
    if (editBtn2) { editBtn2.textContent = "\u2702 Edit"; editBtn2.classList.remove("sp-edit-btn-active"); }
  }
  data.fixes.forEach((_, i) => {
    const chip = document.getElementById(`fixchip-${wId}-${i}`);
    if (chip) chip.classList.toggle("fix-chip-active", i === idx);
  });
  const fix = data.fixes[idx];
  const codeEl = document.getElementById(`after-code-${wId}`);
  if (codeEl) codeEl.innerHTML = renderAfterCode(extractAfterCode(fix));
  // Sync Review Report after block (only if not yet committed)
  const rrEl = document.getElementById("rr-after-code-" + wId);
  if (rrEl && !(window._commitResults || {})[wId]) rrEl.innerHTML = renderAfterCode(extractAfterCode(fix));
  const titleEl = document.getElementById(`fix-title-${wId}`);
  const whyEl = document.getElementById(`fix-why-${wId}`);
  const notesEl = document.getElementById(`fix-notes-${wId}`);
  if (titleEl) titleEl.textContent = fix.title || "";
  const rwEl = document.getElementById(`fix-review-warn-${wId}`); if (rwEl) rwEl.innerHTML = fix.needs_review ? `<div class="fix-review-warning"><span class="fix-review-warning-icon">&#9888;</span><div><strong>Needs manual review</strong><ul>${(fix.validator_warnings || []).map(w => `<li>${escHtml(w)}</li>`).join("")}</ul></div></div>` : "";
  if (whyEl) whyEl.textContent = fix.why || "";
  if (notesEl) notesEl.innerHTML = fix.compliance_notes ? `<strong>Compliance:</strong> ${escHtml(fix.compliance_notes)}` : "";
  const patchWrap = document.getElementById(`patched-wrap-${wId}`);
  if (patchWrap) patchWrap.classList.add("hidden");
  const btn = document.getElementById(`commit-btn-${wId}`);
  if (btn) { btn.disabled = false; btn.textContent = "⬆ Commit Fix to File"; btn.classList.remove("committed"); }
};

window.commitFix = async function (wId) {
  const data = (window._fixData || {})[wId]; if (!data) return;
  const btn = document.getElementById(`commit-btn-${wId}`);
  if (btn) { btn.disabled = true; btn.textContent = "Committing…"; }
  try {
    const fix = data.fixes[data.selectedIdx || 0];
    /* FEATURE 2: use manually edited code if user edited it */
    const afterCode = (data._editedCode != null && data._editedCode !== '')
      ? data._editedCode
      : extractAfterCode(fix);
    const resp = await fetch("/api/commit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ warning_id: wId, patched_code: afterCode, run_id: data.rid || "" })
    });
    const result = await resp.json();
    if (btn) { btn.textContent = "✓ Committed"; btn.classList.add("committed"); btn.disabled = true; }

    const patchWrap = document.getElementById(`patched-wrap-${wId}`);
    const patchTitle = document.getElementById(`patched-file-title-${wId}`);
    const patchBlock = document.getElementById(`patched-code-${wId}`);
    const dlEl = document.getElementById(`download-link-${wId}`);

    if (patchWrap) patchWrap.classList.remove("hidden");
    if (patchTitle) {
      patchTitle.textContent = result.is_full_file
        ? `✓ Full patched file: ${result.original_file || "source.c"}`
        : "✓ Patched code (snippet only — original source file not found)";
    }
    if (patchBlock && result.patched_code) {
      const pStart = result.patch_line_start || 0;
      const pCount = result.patch_line_count || 0;
      const pEnd = pStart ? pStart + pCount - 1 : 0;

      const allLines = result.patched_code.split("\n");
      patchBlock.innerHTML = allLines.map((ln, i) => {
        const num = i + 1;
        const isChanged = pStart > 0 && num >= pStart && num <= pEnd;
        return `<div class="code-row${isChanged ? " patch-highlight" : ""}">` +
          `<span class="ln-num">${num}</span>` +
          `<span class="ln-code">${escHtml(ln)}</span></div>`;
      }).join("");
    }
    if (dlEl && result.download_url) {
      dlEl.href = result.download_url;
      dlEl.download = result.filename || "patched.c";
    }
    // Store commit result so Review Report tab can show full patched file
    window._commitResults = window._commitResults || {};
    window._commitResults[wId] = {
      afterCode,
      runId: data.rid || "",
      patchedCode: result.patched_code || "",
      patchLineStart: result.patch_line_start || 0,
      patchLineCount: result.patch_line_count || 0,
      originalFile: result.original_file || "",
      downloadUrl: result.download_url || "",
      filename: result.filename || "patched.c",
      isFullFile: result.is_full_file || false,
      wasUserEdited: !!(data._editedCode != null && data._editedCode !== '')
    };
    // Persist to sessionStorage so Results page can restore highlight after navigation
    try {
      var _stored = JSON.parse(sessionStorage.getItem("misra_commits") || "{}");
      _stored[wId] = {
        patchLineStart: result.patch_line_start || 0,
        patchLineCount: result.patch_line_count || 0,
        originalFile: result.original_file || "",
        downloadUrl: result.download_url || "",
        filename: result.filename || "patched.c",
        isFullFile: result.is_full_file || false,
        wasUserEdited: !!(data._editedCode != null && data._editedCode !== '')
      };
      sessionStorage.setItem("misra_commits", JSON.stringify(_stored));
    } catch (_se) { }
    // Live-update Review Report after block if card is already open
    if (typeof _rrRefreshAfterBlock === "function") _rrRefreshAfterBlock(wId);
    /* Auto-close side panel if it was opened from the Review Report awaiting-decision button */
    if (window._spOpenedFromRR) {
      setTimeout(function () { window.closeSidePanel(); }, 500);
    }
    // Show small inline undo button in side panel (no browser alert)
    if (btn && !document.getElementById("undo-inline-" + wId)) {
      var _undoBtn = document.createElement("button");
      _undoBtn.id = "undo-inline-" + wId;
      _undoBtn.textContent = "↩ Undo";
      _undoBtn.title = "Revert this fix and restore original file";
      _undoBtn.style.cssText = "margin-left:8px;background:#dc2626;color:#fff;border:none;padding:3px 9px;border-radius:5px;font-size:11px;font-weight:600;cursor:pointer;vertical-align:middle;";
      _undoBtn.onclick = function () { undoCommit(wId); };
      btn.parentElement && btn.parentElement.appendChild(_undoBtn);
    }
    if (patchWrap) patchWrap.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (e) {
    if (btn) { btn.disabled = false; btn.textContent = "⬆ Commit Fix to File"; }
    console.error("Commit failed:", e);
  }
};

/* ============================================================
   REVIEW REPORT — helpers
   ============================================================ */

// Save to Audit Excel (only from Review Report tab)
window.rrSaveAudit = async function (wId) {
  const committed = (window._commitResults || {})[wId];
  const fixData = (window._fixData || {})[wId];
  const statusEl = document.getElementById("rr-audit-status-" + wId);
  const btn = document.getElementById("rr-save-audit-" + wId);
  const afterCode = committed ? committed.afterCode
    : (fixData ? extractAfterCode(fixData.fixes[fixData.selectedIdx || 0]) : "");
  const runId = committed ? committed.runId : (fixData ? (fixData.rid || "") : "");
  if (!afterCode || afterCode === "[fix code not available]") {
    if (statusEl) { statusEl.style.color = "#dc2626"; statusEl.textContent = "⚠ Commit a fix first from View Results."; }
    return;
  }
  if (btn) { btn.disabled = true; btn.textContent = "Saving…"; }
  try {
    const r = await fetch("/api/save_audit", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ warning_id: wId, patched_code: afterCode, run_id: runId })
    });
    const res = await r.json();
    if (res.status === "ok") {
      if (statusEl) { statusEl.style.color = "#065f46"; statusEl.textContent = "✓ Saved → " + (res.audit_path || "Output_excel_after_run/audit_report.xlsx"); }
      if (btn) { btn.textContent = "✓ Saved"; btn.style.background = "#15803d"; }
    } else {
      if (statusEl) { statusEl.style.color = "#dc2626"; statusEl.textContent = "⚠ " + (res.message || "Save failed"); }
      if (btn) { btn.disabled = false; btn.textContent = "💾 Save to Audit Excel"; }
    }
  } catch (e) {
    if (statusEl) { statusEl.style.color = "#dc2626"; statusEl.textContent = "⚠ " + e.message; }
    if (btn) { btn.disabled = false; btn.textContent = "💾 Save to Audit Excel"; }
  }
};

// Undo committed fix (side panel only) — no alert(), inline feedback only
window.undoCommit = async function (wId) {
  const committed = (window._commitResults || {})[wId];
  const fixData = (window._fixData || {})[wId];
  const runId = committed ? committed.runId : (fixData ? (fixData.rid || "") : "");
  const undoBtn = document.getElementById("undo-inline-" + wId);
  if (undoBtn) { undoBtn.disabled = true; undoBtn.textContent = "Reverting…"; }
  try {
    const r = await fetch("/api/revert", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ warning_id: wId, run_id: runId })
    });
    const res = await r.json();
    if (res.status === "ok") {
      /* Clear in-memory commit state */
      if (window._commitResults) delete window._commitResults[wId];
      /* Clear edited code so next commit uses freshly selected fix */
      if (window._fixData && window._fixData[wId]) delete window._fixData[wId]._editedCode;
      /* Remove from sessionStorage so Results page doesn't restore old commit */
      try {
        var _sc = JSON.parse(sessionStorage.getItem("misra_commits") || "{}");
        delete _sc[wId];
        sessionStorage.setItem("misra_commits", JSON.stringify(_sc));
      } catch (_se) { }
      /* Reset commit button */
      const cb = document.getElementById("commit-btn-" + wId);
      if (cb) { cb.disabled = false; cb.textContent = "⬆ Commit Fix to File"; cb.classList.remove("committed"); }
      /* Hide patched-file wrap */
      const pw = document.getElementById("patched-wrap-" + wId);
      if (pw) pw.classList.add("hidden");
      /* Remove undo button */
      if (undoBtn) undoBtn.remove();
      /* Reset Review Report card back to AWAITING DECISION state */
      _rrResetToAwaiting(wId);
      /* Small inline success text */
      const ok = document.createElement("span");
      ok.style.cssText = "font-size:11px;color:#15803d;margin-left:8px;vertical-align:middle;";
      ok.textContent = "✓ Reverted — choose a new fix and commit";
      cb && cb.parentElement && cb.parentElement.appendChild(ok);
      setTimeout(function () { if (ok.parentElement) ok.remove(); }, 3500);
    } else {
      if (undoBtn) { undoBtn.disabled = false; undoBtn.textContent = "↩ Undo"; }
      const err = document.createElement("span");
      err.style.cssText = "font-size:11px;color:#dc2626;margin-left:8px;vertical-align:middle;";
      err.textContent = "⚠ " + (res.error || "Revert failed");
      undoBtn && undoBtn.parentElement && undoBtn.parentElement.appendChild(err);
      setTimeout(function () { if (err.parentElement) err.remove(); }, 4000);
    }
  } catch (e) {
    if (undoBtn) { undoBtn.disabled = false; undoBtn.textContent = "↩ Undo"; }
    const err = document.createElement("span");
    err.style.cssText = "font-size:11px;color:#dc2626;margin-left:8px;vertical-align:middle;";
    err.textContent = "⚠ " + e.message;
    undoBtn && undoBtn.parentElement && undoBtn.parentElement.appendChild(err);
    setTimeout(function () { if (err.parentElement) err.remove(); }, 4000);
  }
};

// Live-update Review Report AFTER block when commit happens from side panel
function _rrRefreshAfterBlock(wId) {
  /* FEATURE 3: If user chose "Go Without Change", show no-change state */
  if ((window._noChangeResults || {})[wId]) {
    _rrMarkNoChange(wId);
    return;
  }
  const committed = (window._commitResults || {})[wId];
  if (!committed || !committed.patchedCode) return;
  const labelEl = document.getElementById("rr-after-label-" + wId);
  const codeEl = document.getElementById("rr-after-code-" + wId);
  const blockEl = document.getElementById("rr-after-block-" + wId);
  const dlEl = document.getElementById("rr-download-" + wId);
  const chipsRow = document.getElementById("fixchips-" + wId);
  if (!codeEl) return; // card not open yet — will render correctly on next open
  /* FIX 5: reveal the chips row now that user has taken action */
  if (chipsRow) chipsRow.style.display = "";
  /* Update border color to green */
  if (blockEl) blockEl.style.borderColor = "rgba(21,128,61,.25)";
  const pStart = committed.patchLineStart || 0;
  const pEnd = pStart ? pStart + (committed.patchLineCount || 0) - 1 : 0;
  codeEl.innerHTML = committed.patchedCode.split("\n").map(function (ln, i) {
    const num = i + 1, isChg = pStart > 0 && num >= pStart && num <= pEnd;
    return `<div class="code-row${isChg ? " patch-highlight" : ""}"><span class="ln-num">${num}</span><span class="ln-code">${escHtml(ln)}</span></div>`;
  }).join("");
  if (labelEl) {
    const fn = committed.originalFile ? ` — <span style="font-weight:500;opacity:.8;">${escHtml(committed.originalFile)}</span>` : "";
    const fixLabel = committed.wasUserEdited
      ? '<span style="font-size:10px;font-weight:600;background:rgba(37,99,235,.12);color:#1d4ed8;padding:1px 8px;border-radius:10px;margin-left:4px;">&#x270E; User-Edited &amp; Committed</span>'
      : '<span style="font-size:10px;font-weight:600;background:rgba(16,185,129,.12);color:#065f46;padding:1px 8px;border-radius:10px;margin-left:4px;">&#x2713; LLM Fix Committed</span>';
    labelEl.style.color = "#15803d";
    labelEl.innerHTML = `&#128994; AFTER (FULL PATCHED FILE)${fn} ${fixLabel}`;
  }
  if (dlEl && committed.downloadUrl)
    dlEl.innerHTML = `<a href="${escHtml(committed.downloadUrl)}" download="${escHtml(committed.filename || "patched.c")}" style="font-size:12px;color:var(--primary,#2563eb);text-decoration:none;display:inline-flex;align-items:center;gap:4px;">&#x2B07; Download patched file</a>`;
}

/* ============================================================
   SHARED HELPERS
   ============================================================ */
function toggleCard(wId) {
  const card = document.querySelector(`.warning-card[data-id="${wId}"]`);
  if (card) card.classList.toggle("open");
}
window.toggleCard = toggleCard;

function renderAfterCode(raw) {
  if (!raw) return "";
  const rows = raw.split("\n").map(ln => { const m = ln.match(/^\s*(\d+)\s*(.*)/); if (!m) { const code = ln.trimEnd(); if (!code) return null; return `<div class="code-row"><span class="ln-num"></span><span class="ln-code">${escHtml(code)}</span></div>`; } const num = m[1], code = m[2].trimEnd(); if (!code.trim()) return `<div class="code-row" style="min-height:3px;padding:0;"><span class="ln-num" style="opacity:.3;">${escHtml(num)}</span><span class="ln-code"></span></div>`; return `<div class="code-row"><span class="ln-num">${escHtml(num)}</span><span class="ln-code">${escHtml(code)}</span></div>`; }).filter(Boolean);
  return rows.join("");
}

function extractAfterCode(fix) {
  if (!fix) return "";
  const codeRaw = fix.patched_code || fix.corrected_code || fix.code_change || fix.fixed_code || fix.code || "";
  let code = "";
  if (typeof codeRaw === "string") code = codeRaw;
  else if (Array.isArray(codeRaw)) code = codeRaw.join("\n");
  else if (codeRaw && typeof codeRaw === "object") code = codeRaw.AFTER || codeRaw.after || codeRaw.code || JSON.stringify(codeRaw, null, 2);
  const afIdx = code.toUpperCase().indexOf("AFTER:");
  if (afIdx !== -1) { code = code.slice(afIdx + 6).trim(); code = code.replace(/^(MISRA Rules Applied|Rationale|Risk Level|Confidence|Note)[^\n]*\n?/gim, "").trim(); }
  else { const beIdx = code.toUpperCase().indexOf("BEFORE:"); if (beIdx !== -1) { const aftIdx2 = code.toUpperCase().indexOf("AFTER:", beIdx); if (aftIdx2 !== -1) code = code.slice(aftIdx2 + 6).trim(); else code = code.slice(beIdx + 7).trim(); } }
  return code || "[fix code not available]";
}

function getRuleText(w) {
  const ctx = w.misra_context || w.retrieved_context || {};
  if (typeof ctx === "string") return ctx.slice(0, 600);
  if (Array.isArray(ctx) && ctx.length) { const chunk = ctx[0]; return chunk.body_text || chunk.rule_text || chunk.text || chunk.amplification || ""; }
  return ctx.body_text || ctx.rule_text || ctx.text || ctx.amplification || "";
}

function friendlyKey(k) { const MAP = { warning_id: "Warning ID", rule_id: "Rule", message: "Message", file_path: "File", severity: "Severity", checker_name: "Checker", misra_rule: "MISRA Rule", category: "Category", rule_category: "Rule Type" }; return MAP[k] || k.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()); }

function formatRuleId(raw) {
  if (!raw) return "";
  const m1 = raw.match(/RULE[-_](\d+)[-_](\d+)/i); if (m1) return `${m1[1]}.${m1[2]}`;
  const m2 = raw.match(/rule\s+(\d+[\._]\d+)/i); if (m2) return m2[1].replace("_", ".");
  const m3 = raw.match(/^(\d+)[_.](\d+)$/); if (m3) return `${m3[1]}.${m3[2]}`;
  return raw;
}

function escHtml(str) { if (str === null || str === undefined) return ""; return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }

function baseName(path) { return (path || "").replace(/\\\\/g, "/").split("/").pop(); }