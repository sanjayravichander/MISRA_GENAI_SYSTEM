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
  let parsedExcelData = [];   // [{fileName, ruleId, message, warningNumbers, functionName}]
  let fileMappings = {};   // { fileName: [warnings] }
  let currentRunId = null;

  /* ── Drop zones ── */
  [excelZone, cZone].forEach(zone => {
    zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("drag-over"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", e => {
      e.preventDefault(); zone.classList.remove("drag-over");
      const files = [...e.dataTransfer.files];
      zone === excelZone ? handleExcel(files[0]) : handleCFiles(files);
    });
    /* No extra click handler needed — input[type=file] covers the entire zone via position:absolute inset:0 */
  });
  excelInput.addEventListener("change", () => handleExcel(excelInput.files[0]));
  cInput.addEventListener("change", () => handleCFiles([...cInput.files]));

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
    const f = cFilesList[idx];
    if (!f) return;
    startAnalysis([f]);
  };

  runAllBtn && runAllBtn.addEventListener("click", () => startAnalysis(cFilesList));

  async function startAnalysis(srcFiles) {
    showError("");
    const progressPanel = document.getElementById("progress-panel");
    const uploadCard = document.getElementById("upload-card");
    progressPanel.classList.add("visible");
    uploadCard.style.opacity = "0.4";
    uploadCard.style.pointerEvents = "none";

    const fd = new FormData();
    fd.append("warning_report", excelFile);
    srcFiles.forEach(f => fd.append("source_files", f));

    const checkedCats = [...document.querySelectorAll('input[name="misra_category"]:checked')].map(c => c.value);
    if (checkedCats.length) {
      sessionStorage.setItem("misra_filter", checkedCats.join(","));
      fd.append("misra_categories", checkedCats.join(","));
    } else {
      sessionStorage.removeItem("misra_filter");
    }

    try {
      const resp = await fetch("/api/analyse", { method: "POST", body: fd });
      const data = await resp.json();
      if (!resp.ok) { showError(data.error || "Server error"); resetUI(); return; }
      currentRunId = data.run_id;
      listenProgress(data.job_id, data.run_id);
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
  function listenProgress(jobId, runId) {
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
    }
    let counterEl = document.getElementById("pr-counter");
    if (!counterEl) {
      counterEl = document.createElement("div"); counterEl.id = "pr-counter"; counterEl.className = "pr-counter";
      counterEl.textContent = "Waiting for records\u2026";
      progressPanel.insertBefore(counterEl, recordsWrap);
    }

    /* Side panel */
    let sidePanel = document.getElementById("pr-side-panel");
    if (!sidePanel) {
      sidePanel = document.createElement("div"); sidePanel.id = "pr-side-panel"; sidePanel.className = "pr-side-panel";
      sidePanel.innerHTML = `
        <div class="pr-side-inner">
          <div class="pr-side-header">
            <div class="pr-side-title" id="pr-side-title">Result</div>
            <button class="pr-side-close" onclick="closeSidePanel()" title="Close">&#x2715;</button>
          </div>
          <div class="pr-side-body" id="pr-side-body">
            <div class="pr-side-loading"><div class="ld"></div><div class="ld"></div><div class="ld"></div><span class="ld-text">Loading\u2026</span></div>
          </div>
        </div>
        <div class="pr-side-backdrop" onclick="closeSidePanel()"></div>`;
      document.body.appendChild(sidePanel);
    }

    window.closeSidePanel = function () { sidePanel.classList.remove("pr-side-open"); document.body.classList.remove("pr-panel-open"); };
    window.openSidePanel = async function (wid, rid) {
      sidePanel.classList.add("pr-side-open"); document.body.classList.add("pr-panel-open");
      document.getElementById("pr-side-title").textContent = "Warning " + wid;
      const body = document.getElementById("pr-side-body");
      body.innerHTML = `<div class="pr-side-loading"><div class="ld"></div><div class="ld"></div><div class="ld"></div><span class="ld-text">Loading result\u2026</span></div>`;
      try {
        const resp = await fetch("/api/result/" + rid);
        const data = await resp.json();
        const warnings = data.warnings || [];
        const w = warnings.find(x => String(x.warning_id) === String(wid)) || warnings[0];
        if (!w) { body.innerHTML = `<div class="error-panel">Record not found.</div>`; return; }
        body.innerHTML = buildSidePanelContent(w, rid);
        window._fixData = window._fixData || {};
        const fixes = w.ranked_fixes || w.fix_suggestions || w.fixes || [];
        window._fixData[wid] = { fixes, beforeCode: w._source_context || w.source_context || "", selectedIdx: 0 };
      } catch (e) {
        body.innerHTML = `<div class="error-panel">Failed to load: ${escHtml(e.message)}</div>`;
      }
    };

    function buildSidePanelContent(w, rid) {
      const ev = w.evaluation || w.evaluator_result || {};
      const wid = String(w.warning_id || "");
      const ruleId = formatRuleId(w.rule_id || w.misra_rule || "");
      const msg = w.message || w.warning_message || "";
      const sev = (w.severity || "").toLowerCase();
      const fp = w.file_path ? w.file_path.replace(/\\\\/g, "/").split("/").pop() : "";
      const fixes = w.ranked_fixes || w.fix_suggestions || w.fixes || [];
      let html = `<div class="sp-meta">
        ${ruleId ? `<span class="w-rule-pill">Rule ${escHtml(ruleId)}</span>` : ""}
          ${fp ? `<span class="sp-file">${escHtml(fp)}</span>` : ""}
      </div>
      ${msg ? `<div class="sp-msg">${escHtml(msg)}</div>` : ""}`;
      const src = w._source_context || w.source_context || "";
      const srcTxt = typeof src === "string" ? src : Array.isArray(src) ? src.join("\n") : (src && src.context_text) ? src.context_text : "";
      if (srcTxt) {
        const rows = srcTxt.split("\n").map(ln => { const clean = ln.replace(/^\s*>>>/, "   "); const m = clean.match(/^\s*(\d+)\s+(.*)/); if (!m || !m[2].trim()) return null; return `<div class="code-row"><span class="ln-num">${escHtml(m[1])}</span><span class="ln-code">${escHtml(m[2].trimEnd())}</span></div>`; }).filter(Boolean);
        if (rows.length) html += `<div class="detail-section"><div class="detail-section-title">Source Code</div><div class="source-block">${rows.join("")}</div></div>`;
      }
      if (fixes.length) {
        window._fixData = window._fixData || {}; window._fixData[wid] = { fixes, beforeCode: srcTxt, selectedIdx: 0 };
        const chips = fixes.map((f, i) => `<button class="fix-chip ${i === 0 ? "fix-chip-active" : ""}" id="fixchip-${escHtml(wid)}-${i}" onclick="selectFixChip('${escHtml(wid)}',${i})" title="${escHtml(f.title || f.fix_title || "Fix " + (i + 1))}">Fix ${i + 1}${(f.source === "db_template" || f.db_verified === true) ? '<span class="fix-chip-db">DB</span>' : ""}  </button>`).join("");
        html += `<div class="detail-section"><div class="detail-section-title">Fix Suggestion</div>
          <div class="fix-chips-row">${chips}<span class="fix-chip-label" id="fix-chip-desc-${escHtml(wid)}">${escHtml(fixes[0].title || fixes[0].why || "")}</span></div>
          <div class="fix-after-wrap"><div class="fix-after-header"><span class="fix-after-label">After (fix applied)</span><span class="fix-active-tag" id="fix-active-tag-${escHtml(wid)}">Fix 1 selected</span></div>
          <div class="code-diff-panel after" id="after-block-${escHtml(wid)}"><div class="code-diff-label">After<button class="commit-inline-btn" id="commit-btn-${escHtml(wid)}" onclick="commitFix('${escHtml(wid)}')" title="Commit this fix">&#x2B06; Commit Fix</button></div>
          <div id="after-code-${escHtml(wid)}">${renderAfterCode(extractAfterCode(fixes[0]))}</div>
          <div class="commit-inline-status hidden" id="commit-status-${escHtml(wid)}">&#x2713; Patch applied &nbsp;<a class="download-link" id="download-link-${escHtml(wid)}" href="#" download>&#x2B07; Download</a></div>
          </div></div></div>`;
      }
      html += `<div class="sp-full-link"><a href="/results/${escHtml(rid)}" class="btn btn-primary btn-sm">View Full Report &#8594;</a></div>`;
      return html;
    }

    /* Per-record tracking */
    const recordMeta = {}; let totalWarnings = 0, doneCount = 0;
    const PHASE_COL = { "6a": 0, "6b": 1, "7": 2, "8": 3, "done": 4 };
    const PHASE_LABEL = { "6a": "Read", "6b": "Rules", "7": "Fix", "8": "Check", "done": "Done" };
    const PHASE_PCT = { "6a": 15, "6b": 35, "7": 65, "8": 88, "done": 100 };

    function ensureRecord(wid) {
      if (recordMeta[wid]) return recordMeta[wid];
      const card = document.createElement("div"); card.className = "pr-card stream-new"; card.id = "prcard-" + wid;
      setTimeout(() => card.classList.remove("stream-new"), 600);
      const steps = ["6a", "6b", "7", "8", "done"];
      card.innerHTML = `<div class="pr-header"><span class="pr-wid">${escHtml(wid)}</span><span class="pr-status-badge pr-running" id="prstatus-${escHtml(wid)}">Processing\u2026</span><button class="pr-view-btn hidden" id="prview-${escHtml(wid)}" onclick="openSidePanel('${escHtml(wid)}','__RID__')">View Result &#8594;</button></div>
        <div class="pr-stepper">${steps.map((ph, i) => `<div class="pr-step" id="prstep-${escHtml(wid)}-${ph}"><div class="pr-step-circle">${i + 1}</div><div class="pr-step-label">${PHASE_LABEL[ph]}</div></div>${i < steps.length - 1 ? `<div class="pr-step-line" id="prline-${escHtml(wid)}-${ph}"></div>` : ""}`).join("")}</div>
        <div class="pr-bar-wrap"><div class="pr-bar-track"><div class="pr-bar-fill" id="prbar-${escHtml(wid)}" style="width:0%"></div></div><span class="pr-bar-pct" id="prpct-${escHtml(wid)}">0%</span></div>`;
      recordsWrap.appendChild(card);
      const meta = { card, statusBadge: card.querySelector(`#prstatus-${wid}`), viewBtn: card.querySelector(`#prview-${wid}`), barFill: card.querySelector(`#prbar-${wid}`), barPct: card.querySelector(`#prpct-${wid}`) };
      recordMeta[wid] = meta; return meta;
    }

    function setPhase(wid, phase, isDone) {
      const meta = recordMeta[wid]; if (!meta) return; const colIdx = PHASE_COL[phase]; if (colIdx === undefined) return;
      ["6a", "6b", "7", "8", "done"].forEach((ph, i) => {
        const circle = meta.card.querySelector(`#prstep-${wid}-${ph} .pr-step-circle`);
        const line = meta.card.querySelector(`#prline-${wid}-${ph}`);
        const step = meta.card.querySelector(`#prstep-${wid}-${ph}`);
        if (!circle || !step) return;
        if (i < colIdx) { step.classList.add("pr-step-done"); step.classList.remove("pr-step-active"); circle.textContent = "\u2713"; if (line) line.classList.add("pr-line-done"); }
        else if (i === colIdx) { if (isDone) { step.classList.add("pr-step-done"); step.classList.remove("pr-step-active"); circle.textContent = "\u2713"; if (line) line.classList.add("pr-line-done"); } else { step.classList.add("pr-step-active"); step.classList.remove("pr-step-done"); } }
      });
      const pct = PHASE_PCT[phase] || 0;
      if (meta.barFill) meta.barFill.style.width = pct + "%"; if (meta.barPct) meta.barPct.textContent = pct + "%";
    }

    function markDone(wid, rid) {
      const meta = recordMeta[wid]; if (!meta || meta.card.classList.contains("pr-card-done")) return; doneCount++;
      /* Mark all circles done at once */
      ["6a", "6b", "7", "8", "done"].forEach(ph => {
        const circle = meta.card.querySelector("#prstep-" + wid + "-" + ph + " .pr-step-circle");
        const line = meta.card.querySelector("#prline-" + wid + "-" + ph);
        const step = meta.card.querySelector("#prstep-" + wid + "-" + ph);
        if (step) { step.classList.add("pr-step-done"); step.classList.remove("pr-step-active"); }
        if (circle) circle.textContent = "\u2713";
        if (line) line.classList.add("pr-line-done");
      });
      /* Jump bar to 100% instantly — no transition lag */
      if (meta.barFill) { meta.barFill.style.transition = "none"; meta.barFill.style.width = "100%"; }
      if (meta.barPct) { meta.barPct.textContent = "100%"; }
      if (meta.statusBadge) { meta.statusBadge.className = "pr-status-badge pr-done"; meta.statusBadge.textContent = "Complete"; }
      meta.card.classList.add("pr-card-done");
      if (meta.viewBtn && rid) { meta.viewBtn.setAttribute("onclick", meta.viewBtn.getAttribute("onclick").replace("__RID__", rid)); meta.viewBtn.classList.remove("hidden"); }
      /* Update badge on fmap card */
      cFilesList.forEach((f, i) => {
        if (f && wid.startsWith(f.name.replace(/\.c$/i, "")) || true) {
          /* update fmap badge if we can match */
          const badge = document.getElementById("fmap-badge-" + i);
          if (badge && badge.textContent === "Running") badge.textContent = "Done";
        }
      });
      counterEl.textContent = `${doneCount} of ${totalWarnings || "?"} records complete`;
      counterEl.className = "pr-counter" + (doneCount === totalWarnings ? " pr-counter-done" : "");
    }

    const PHASE_MAP = { "6a": "ph-6a", "6b": "ph-6b", "7": "ph-7", "8": "ph-8" };
    const es = new EventSource(`/api/progress/${jobId}`);
    es.onmessage = evt => {
      let msg; try { msg = JSON.parse(evt.data); } catch { return; }
      if (msg.type === "heartbeat") return;
      if (msg.phase && PHASE_MAP[msg.phase]) {
        const phEl = document.getElementById(PHASE_MAP[msg.phase]);
        if (phEl) {
          if (msg.type === "phase_start") { document.querySelectorAll(".phase-item").forEach(el => el.classList.remove("active")); phEl.classList.add("active"); const det = phEl.querySelector(".phase-detail"); if (det) det.textContent = plainDetail(msg.detail); }
          else if (msg.type === "phase_done") { phEl.classList.remove("active"); phEl.classList.add("done"); const b = phEl.querySelector(".phase-badge"); if (b) b.textContent = "\u2713"; }
        }
      }
      if (msg.label && statusLn) statusLn.textContent = plainEnglish(msg.label, msg.detail);
      else if (msg.type === "detail" && msg.detail && statusLn) statusLn.textContent = plainDetail(msg.detail);
      if (msg.type === "warning_start" && typeof msg.pct === "number" && totalWarnings === 0 && msg.pct > 0) totalWarnings = Math.round(100 / msg.pct);
      if (msg.total) totalWarnings = msg.total;
      if (msg.warning_id) {
        const wid = msg.warning_id; ensureRecord(wid);
        if (msg.type === "warning_start") {
          const ph = msg.phase || "7";
          if (ph === "8") { ["6a", "6b", "7"].forEach(p => setPhase(wid, p, true)); setPhase(wid, "8", false); }
          else if (ph === "7") { ["6a", "6b"].forEach(p => setPhase(wid, p, true)); setPhase(wid, "7", false); }
          else if (ph === "6b") { setPhase(wid, "6a", true); setPhase(wid, "6b", false); }
          else setPhase(wid, ph, false);
          recordMeta[wid].card.scrollIntoView({ behavior: "smooth", block: "nearest" });
        } else if (msg.type === "warning_done") markDone(wid, runId);
      }
      if (msg.type === "done") {
        es.close(); const targetId = msg.run_id || runId || jobId;
        document.querySelectorAll(".phase-item").forEach(el => { el.classList.remove("active"); el.classList.add("done"); const b = el.querySelector(".phase-badge"); if (b) b.textContent = "\u2713"; });
        Object.keys(recordMeta).forEach(wid => markDone(wid, targetId));
        if (statusLn) statusLn.textContent = "All done! Click any record to view its result.";
        counterEl.textContent = `All ${totalWarnings} records complete`; counterEl.className = "pr-counter pr-counter-done";
      }
      if (msg.type === "error") {
        es.close();
        document.querySelectorAll(".phase-item.active").forEach(el => { el.classList.remove("active"); el.classList.add("error"); });
        if (statusLn) statusLn.textContent = "Something went wrong. Please try again.";
        const ep = document.createElement("div"); ep.className = "error-panel mt-16"; ep.textContent = msg.message || msg.detail || "Unknown error"; progressPanel.appendChild(ep);
        resetUI();
      }
    };
    es.onerror = () => { es.close(); if (statusLn) statusLn.textContent = "Connection lost."; };
  }

  function plainEnglish(label, detail) {
    // Special case: suppress technical model-loading detail
    if (label && label.toLowerCase().includes("launch")) return "Starting up — loading AI model into memory\u2026";
    if (detail && detail.toLowerCase().includes("launch")) return "Loading AI model\u2026 this takes ~30s on first run";
    let s = label + (detail ? " \u2014 " + detail : "");
    [[/phase\s*6a/gi, "Step 1"], [/phase\s*6b/gi, "Step 2"], [/phase\s*7/gi, "Step 3"], [/phase\s*8/gi, "Step 4"], [/parsing/gi, "Reading"], [/qdrant|faiss|bge|embedding/gi, "rule lookup"], [/llm|llama|mistral|model/gi, "AI engine"], [/launching analysis engine/gi, "Loading AI model"]].forEach(([rx, rep]) => { s = s.replace(rx, rep); });
    return s;
  }
  function plainDetail(d) { if (!d) return ""; return d.replace(/qdrant|faiss|bge|embedding/gi, "rule lookup").replace(/llm|llama|mistral/gi, "AI engine").replace(/parsed_warnings?/gi, "warnings read"); }
}

/* ============================================================
   SETTINGS MODAL  (Rule Config)
   ============================================================ */
var _ruleState = { selected: new Set(), overrides: {}, built: false };
window._ruleState = _ruleState;

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
  applyRulePreset(btn.dataset.preset);
};

/* Filter modal to only show rules of a given severity */
window.filterModalToSev = function (sev) {
  RULES_DATA.forEach(r => {
    const row = document.getElementById("mrow-" + cssId(r.id));
    if (row) row.style.display = (r.sev === sev) ? "" : "none";
  });
};

function applyRulePreset(preset) {
  _ruleState.selected.clear();
  const sevMap = { M: ["M"], R: ["R"], A: ["A"], ALL: ["M", "R", "A"], NONE: [] };
  const sevs = sevMap[preset] || [];
  RULES_DATA.forEach(r => { if (sevs.indexOf(r.sev) > -1) _ruleState.selected.add(r.id); });
  RULES_DATA.forEach(r => {
    const cb = document.getElementById("mrcb-" + cssId(r.id));
    const row = document.getElementById("mrow-" + cssId(r.id));
    if (cb) cb.checked = _ruleState.selected.has(r.id);
    if (row) row.classList.toggle("mrow-selected", _ruleState.selected.has(r.id));
  });
  updateModalSummary();
}

function cssId(id) { return id.replace(/\./g, "_").replace(/\s/g, "-"); }

function buildModalRuleList() {
  const container = document.getElementById("modal-rule-list");
  if (!container) return;
  container.innerHTML = "";

  const groups = { M: [], R: [], A: [] };
  RULES_DATA.forEach(r => groups[r.sev].push(r));
  const gInfo = { M: { label: "Mandatory", cls: "rc-sev-m" }, R: { label: "Required", cls: "rc-sev-r" }, A: { label: "Advisory", cls: "rc-sev-a" } };

  ["M", "R", "A"].forEach(sev => {
    const rules = groups[sev]; if (!rules.length) return;
    const gi = gInfo[sev];

    const grpHeader = document.createElement("div");
    grpHeader.className = "mgroup-header";
    grpHeader.innerHTML = `<span class="rc-sev ${gi.cls}">${sev}</span><span class="mgroup-label">${gi.label} Rules</span><span class="rule-count-badge">${rules.length}</span>
      <div class="mgroup-actions">
        <button class="rga-btn" onclick="selectModalGroup('${sev}',true)">Select all</button>
        <button class="rga-btn" style="color:var(--text-muted)" onclick="selectModalGroup('${sev}',false)">Deselect all</button>
      </div>`;
    container.appendChild(grpHeader);

    rules.forEach(r => {
      const warn = r.warnings.length > 12
        ? r.warnings.slice(0, 12).join(", ") + " +" + (r.warnings.length - 12) + " more"
        : r.warnings.join(", ");

      /* Override options: exclude the rule's own severity */
      const ovOpts = ["M", "R", "A"].filter(s => s !== r.sev);
      const ov = _ruleState.overrides[r.id] || null;
      const ovBtns = ovOpts.map(s => {
        const lbl = { M: "Mandatory", R: "Required", A: "Advisory" }[s];
        const active = ov === s ? "rc-ov-" + s.toLowerCase() : "";
        return `<button class="rc-ov-btn ${active}" title="Override to ${lbl}" onclick="setModalOverride('${r.id}','${s}',this)">${s}</button>`;
      }).join("");

      const row = document.createElement("div");
      row.className = "mrow"; row.id = "mrow-" + cssId(r.id);
      if (_ruleState.selected.has(r.id)) row.classList.add("mrow-selected");
      row.innerHTML = `
        <div class="mrow-left">
          <input type="checkbox" class="rc-cb" id="mrcb-${cssId(r.id)}"
            ${_ruleState.selected.has(r.id) ? "checked" : ""}
            onchange="toggleModalRule('${r.id}',this.checked)">
          <div class="mrow-info">
            <div class="mrow-top">
              <span class="rc-sev ${gi.cls}">${r.sev}</span>
              <span class="rc-id">${r.is_dir ? "Dir " : "Rule "}${r.id}</span>
              ${r.is_dir ? "<span class=\"rc-dir-tag\">Directive</span>" : ""}
            </div>
            <div class="mrow-warns" title="${r.warnings.join(", ")}">&#x26A0; ${escHtml(warn)}</div>
          </div>
        </div>
        <div class="mrow-override">
          <span class="rc-ov-label">Override to:</span>
          ${ovBtns}
          <span class="rc-ov-default">default: ${{ M: "Mandatory", R: "Required", A: "Advisory" }[r.sev]}</span>
        </div>`;
      container.appendChild(row);
    });
  });

  updateModalSummary();
}

window.toggleModalRule = function (id, checked) {
  if (checked) _ruleState.selected.add(id); else _ruleState.selected.delete(id);
  const row = document.getElementById("mrow-" + cssId(id));
  if (row) row.classList.toggle("mrow-selected", checked);
  updateModalSummary();
};

window.setModalOverride = function (id, sev, btn) {
  const current = _ruleState.overrides[id];
  btn.parentElement.querySelectorAll(".rc-ov-btn").forEach(b => b.className = "rc-ov-btn");
  if (current === sev) { delete _ruleState.overrides[id]; }
  else { _ruleState.overrides[id] = sev; btn.classList.add("rc-ov-" + sev.toLowerCase()); }
  updateModalSummary();
};

window.selectModalGroup = function (sev, select) {
  RULES_DATA.filter(r => r.sev === sev).forEach(r => {
    if (select) _ruleState.selected.add(r.id); else _ruleState.selected.delete(r.id);
    const cb = document.getElementById("mrcb-" + cssId(r.id));
    const row = document.getElementById("mrow-" + cssId(r.id));
    if (cb) cb.checked = select;
    if (row) row.classList.toggle("mrow-selected", select);
  });
  updateModalSummary();
};

window.filterModalRules = function () {
  const q = (document.getElementById("modal-rule-search") || {}).value || "";
  const ql = q.trim().toLowerCase();
  RULES_DATA.forEach(r => {
    const row = document.getElementById("mrow-" + cssId(r.id));
    if (!row) return;
    const match = !ql || r.id.toLowerCase().includes(ql) || r.warnings.some(w => w.includes(ql));
    row.style.display = match ? "" : "none";
  });
};

function updateModalSummary() {
  let tot = 0, m = 0, rv = 0, a = 0;
  _ruleState.selected.forEach(id => {
    const rule = RULES_DATA.find(x => x.id === id); if (!rule) return; tot++;
    const eff = _ruleState.overrides[id] || rule.sev;
    if (eff === "M") m++; else if (eff === "R") rv++; else a++;
  });
  const sc = document.getElementById("modal-sel-count"); if (sc) sc.textContent = tot;
  const mv = document.getElementById("modal-m-val"); if (mv) mv.textContent = m + " Mandatory";
  const rv2 = document.getElementById("modal-r-val"); if (rv2) rv2.textContent = rv + " Required";
  const av = document.getElementById("modal-a-val"); if (av) av.textContent = a + " Advisory";
}

/* ============================================================
   RESULTS PAGE
   ============================================================ */
function initResultsPage() {
  const root = document.getElementById("results-root");
  const runId = window.MISRA_RUN_ID;
  let allWarnings = [];
  loadResult();

  async function loadResult() {
    try {
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
    } catch (err) { root.innerHTML = `<div class="error-panel">Failed to load: ${escHtml(err.message)}</div>`; }
  }

  function buildShell(data) {
    const s = data.summary || {};
    const total = s.total ?? (data.warnings || []).length;
    const manual = s.manual ?? 0;
    return `
    <div style="padding:40px 0 28px;border-bottom:1px solid var(--border);margin-bottom:28px;">
      <div class="hero-eyebrow" style="margin-bottom:12px;"><span class="hero-eyebrow-dot"></span>Run ${escHtml(data.run_id)}</div>
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
        card.style.display = misraOk ? "" : "";
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
  const rt = (w.rule_type || "").toLowerCase();
  if (rt === "mandatory") return "mandatory"; if (rt === "required") return "required"; if (rt === "advisory") return "advisory";
  const cat = (w.rule_category || w.misra_category || "").toLowerCase();
  if (cat.includes("mandatory")) return "mandatory"; if (cat.includes("required")) return "required"; if (cat.includes("advisory")) return "advisory";
  const ctx = w.misra_context || w.retrieved_context || [];
  if (Array.isArray(ctx)) { for (const chunk of ctx) { const g = (chunk.guidelines || chunk.description || "").toLowerCase(); if (g.includes("(mandatory)")) return "mandatory"; if (g.includes("(required)")) return "required"; if (g.includes("(advisory)")) return "advisory"; } }
  return "";
}

function buildWarningDetail(w, ev, isReview, wId) {
  let html = "";
  if (isReview) html += `<div class="review-banner mt-16"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg> Flagged for manual review.</div>`;

  /* Warning details table */
  const SKIP = new Set(["source_context", "source_lines", "misra_context", "retrieved_context", "line_start", "line_end", "_excel_row", "_source_context", "_from_cache", "evaluation", "evaluator_result", "ranked_fixes", "fix_suggestions", "fixes"]);
  const row = w._excel_row || {};
  const rowKeys = Object.keys(row).filter(k => !SKIP.has(k) && row[k] && String(row[k]).trim());
  if (rowKeys.length) html += `<div class="detail-section"><div class="detail-section-title">Warning Details</div><table class="excel-table">${rowKeys.map(k => `<tr><td>${escHtml(friendlyKey(k))}</td><td>${escHtml(String(row[k]))}</td></tr>`).join("")}</table></div>`;

  /* Source code — NO highlight */
  const srcCtxRaw = w._source_context || w.source_context || w.source_code || "";
  let sourceCode = "";
  if (typeof srcCtxRaw === "string") sourceCode = srcCtxRaw;
  else if (Array.isArray(srcCtxRaw)) sourceCode = srcCtxRaw.join("\n");
  else if (srcCtxRaw && typeof srcCtxRaw === "object") sourceCode = srcCtxRaw.context_text || srcCtxRaw.code || srcCtxRaw.text || srcCtxRaw.content || srcCtxRaw.source || "";

  if (sourceCode) {
    const parsed = sourceCode.split("\n").map(ln => { const clean = ln.replace(/^\s*>>>/, "   "); const m = clean.match(/^\s*(\d+)\s+(.*)/); if (!m || !m[2].trim()) return null; return { num: m[1], code: m[2].trimEnd() }; }).filter(Boolean);
    if (parsed.length) html += `<div class="detail-section"><div class="detail-section-title">Source Code</div><div class="source-block" id="src-${escHtml(wId)}">${parsed.map(({ num, code }) => `<div class="code-row"><span class="ln-num">${escHtml(num)}</span><span class="ln-code">${escHtml(code)}</span></div>`).join("")}</div></div>`;
  }

  /* Explanation — render all sub-fields */
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

  /* Risk analysis — render all sub-fields */
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

  /* Rule text */
  const ruleText = getRuleText(w);
  if (ruleText) html += `<div class="detail-section"><div class="detail-section-title">Rule ${escHtml(formatRuleId(w.rule_id || ""))}</div><div class="info-box">${escHtml(ruleText)}</div></div>`;

  /* Fix suggestion — chips + After panel + Commit button INSIDE after block */
  const fixes = w.ranked_fixes || w.fix_suggestions || w.fixes || [];
  if (fixes.length) {
    window._fixData = window._fixData || {};
    window._fixData[wId] = { fixes, beforeCode: sourceCode, selectedIdx: 0 };
    const firstAfter = extractAfterCode(fixes[0]);
    const chips = fixes.map((f, i) => { const isDB = f.source === "db_template" || f.db_verified === true; return `<button class="fix-chip ${i === 0 ? "fix-chip-active" : ""}" id="fixchip-${escHtml(wId)}-${i}" onclick="selectFixChip('${escHtml(wId)}',${i})" title="${escHtml(f.title || f.fix_title || "Fix " + (i + 1))}">Fix ${i + 1}${isDB ? '<span class="fix-chip-db">DB</span>' : ""}  </button>`; }).join("");
    html += `<div class="detail-section"><div class="detail-section-title">Fix Suggestion</div>
      <div class="fix-chips-row" id="fixchips-${escHtml(wId)}">${chips}<span class="fix-chip-label" id="fix-chip-desc-${escHtml(wId)}">${escHtml(fixes[0].title || fixes[0].fix_title || fixes[0].why || "")}</span></div>
      <div class="fix-after-wrap">
        <div class="fix-after-header"><span class="fix-after-label">After (fix applied)</span><span class="fix-active-tag" id="fix-active-tag-${escHtml(wId)}">Fix 1 selected</span></div>
        <div class="code-diff-panel after" id="after-block-${escHtml(wId)}">
          <div class="code-diff-label">After
            <button class="commit-inline-btn" id="commit-btn-${escHtml(wId)}" onclick="commitFix('${escHtml(wId)}')" title="Commit this fix">&#x2B06; Commit Fix</button>
          </div>
          <div id="after-code-${escHtml(wId)}">${renderAfterCode(firstAfter)}</div>
          <div class="commit-inline-status hidden" id="commit-status-${escHtml(wId)}">&#x2713; Patch applied &nbsp;<a class="download-link" id="download-link-${escHtml(wId)}" href="#" download>&#x2B07; Download patched file</a></div>
        </div>
      </div>
    </div>`;
    const evalNotes = ev.evaluator_notes || ev.notes || ev.summary || "";
    if (evalNotes) html += `<div class="info-box eval-note" style="margin-top:10px;">${escHtml(evalNotes)}</div>`;
  } else {
    html += `<div class="detail-section"><div class="detail-section-title">Fix Suggestion</div><div class="info-box" style="color:var(--text-muted);font-style:italic;">No fix suggestions available for this warning.</div></div>`;
  }

  /* Deviation note — render all sub-fields */
  const devRaw = w.deviation_advice || ev.deviation_advice || "";
  if (devRaw) {
    let devHtml = "";
    if (typeof devRaw === "object" && devRaw) {
      const lm = { deviation_possible: "Deviation possible", recommended_decision: "Recommended action", required_justification: "Justification required", review_notes: "Review notes" };
      devHtml = Object.entries(devRaw).filter(([, v]) => v && String(v).trim()).map(([k, v]) => `<div style="margin-bottom:6px;"><span style="font-weight:600;color:var(--text);">${escHtml(lm[k] || k.replace(/_/g, " "))}:</span> <span style="color:var(--text-sub);">${escHtml(String(v))}</span></div>`).join("");
    } else devHtml = escHtml(String(devRaw));
    if (devHtml) html += `<div class="detail-section"><div class="detail-section-title">Exception / Deviation Note</div><div class="info-box deviation">${devHtml}</div></div>`;
  }

  return html || `<div class="text-muted mt-16" style="font-size:12px;">No details available.</div>`;
}

/* ============================================================
   FIX CHIP SELECTOR + COMMIT
   ============================================================ */
window.selectFixChip = function (wId, idx) {
  const data = (window._fixData || {})[wId]; if (!data) return;
  data.selectedIdx = idx;
  data.fixes.forEach((_, i) => { const chip = document.getElementById(`fixchip-${wId}-${i}`); if (chip) chip.classList.toggle("fix-chip-active", i === idx); });
  const fix = data.fixes[idx];
  const newCode = extractAfterCode(fix);
  const codeEl = document.getElementById(`after-code-${wId}`);
  const tagEl = document.getElementById(`fix-active-tag-${wId}`);
  const descEl = document.getElementById(`fix-chip-desc-${wId}`);
  if (codeEl) codeEl.innerHTML = renderAfterCode(newCode);
  if (tagEl) tagEl.textContent = `Fix ${idx + 1} selected`;
  if (descEl) descEl.textContent = fix.title || fix.fix_title || fix.why || "";
};

window.commitFix = async function (wId) {
  const data = (window._fixData || {})[wId]; if (!data) return;
  const btn = document.getElementById(`commit-btn-${wId}`);
  if (btn) { btn.disabled = true; btn.textContent = "Committing\u2026"; }
  try {
    const fix = data.fixes[data.selectedIdx || 0];
    const afterCode = extractAfterCode(fix);
    const resp = await fetch("/api/commit", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ warning_id: wId, patched_code: afterCode }) });
    const result = await resp.json();
    if (btn) { btn.textContent = "\u2713 Committed"; btn.classList.add("committed"); }
    const statusEl = document.getElementById(`commit-status-${wId}`);
    const dlEl = document.getElementById(`download-link-${wId}`);
    if (statusEl) statusEl.classList.remove("hidden");
    if (dlEl && result.download_url) { dlEl.href = result.download_url; dlEl.style.display = "inline-flex"; }
  } catch (e) { if (btn) { btn.disabled = false; btn.textContent = "\u2B06 Commit Fix"; } }
};

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