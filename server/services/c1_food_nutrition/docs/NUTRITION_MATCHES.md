# Which table entry each food class uses

**Written:** 2026-10-16, from `src/c1_food_nutrition/ml/data/class_concepts.csv` and the table names in `data/c1/c1_foods_combined.csv`. No nutrient values are listed here (the table is not committed; values come from the Sri Lankan Food Composition Database, Opatha et al., 2025, and USDA FoodData Central).

Each class the model can name is matched to one entry of the composition table. **exact** = the same dish; **close** = the same dish, a variety may differ; **partial** = the nearest entry, noticeably different (the response carries a note); **none** = no honest match, the nutrients stay unknown (`null`). A food is never given the values of a broad concept. To change a match, edit the CSV (`food_id`, `match`, `note`) and run the tests.

The owner chose the seven rows marked "owner choice 2026-10-18". The other `partial`, `close` and `none` rows are still to be reviewed. No honest match exists for `asmi`, `brinjal_dish`, `cutlet`, `kokis`, `konda_kewum`, `lunu_miris`, `mun_kewum`, `pappadam`, `shrimp_curry` and `watalappam` (USDA offers only a raw cutlet, doughnuts, puffed rice cakes, unfried papad, shrimp without gravy, flan and plain eggplant); the owner declined the papad, shrimp and flan proposals and chose to keep brinjal null.

| Class | Match | Table entry | Note |
|---|---|---|---|
| basmati_rice | exact | SL_1 Rice, Basmati, Boiled | Rice, Basmati, Boiled |
| basmati_rice_cooked | exact | SL_1 Rice, Basmati, Boiled | Rice, Basmati, Boiled |
| beetroot_curry | exact | SL_71 Beetroot Curry | Beetroot Curry |
| bitter_gourd_curry | exact | SL_84 Bittergourd Curry | Bittergourd Curry |
| boiled_egg | exact | SL_165 Egg, Boiled | Egg, Boiled |
| cashew_curry | exact | SL_208 Cashew Curry | Cashew Curry |
| coca_cola | exact | SL_233 Coca Cola | Coca Cola |
| hoppers | exact | SL_37 Hoppers | Hoppers |
| kiribath | exact | SL_9 Milk Rice, White | Milk Rice, White |
| mallum | exact | SL_66 Mallum | Mallum |
| pastry | exact | SL_16 Pastry | Pastry |
| pittu | exact | SL_42 Pittu | Pittu |
| pol_sambol | exact | SL_202 Coconut Sambol | Coconut Sambol |
| soya_curry | exact | SL_57 Soya Curry | Soya Curry |
| vegetable_salad | exact | SL_69 Vegetable Salad | Vegetable Salad |
| bean_curry | close | SL_70 Beans Curry | Beans Curry; the photos may show other beans |
| potato_milk_curry | close | SL_47 Potato Curry, White | Potato Curry, White |
| red_rice_cooked | close | SL_3 Rice, Red Kekulu, Boiled | Rice, Red Kekulu, Boiled |
| samba_rice_cooked | close | SL_4 Rice, Samba, Boiled | Rice, Samba, Boiled |
| chicken_bun | partial | SL_11 Bun | plain Bun; the filling is not included |
| egg_bun | partial | SL_11 Bun | plain Bun; the filling is not included |
| fish_bun | partial | SL_11 Bun | plain Bun; the filling is not included |
| fried_potato | partial | SL_48 Tempered Potato | Tempered Potato |
| gotukola_mallum | partial | SL_66 Mallum | generic Mallum, not gotukola specifically |
| kimbula_bun | partial | SL_11 Bun | plain Bun; the filling is not included |
| kottu | partial | SL_31 Chicken Kottu Roti | Chicken Kottu Roti; other kottu types differ |
| pizza | partial | SL_24 Cheese Pizza - Pizza Hut | Cheese Pizza - Pizza Hut; other toppings differ |
| roll | partial | SL_15 Chinese Rolls | Chinese Rolls; fried rolls with other fillings differ |
| roti | partial | SL_29 Coconut Roti | Coconut Roti; other rotis differ |
| string_hoppers | partial | SL_35 String Hoppers, White | String Hoppers, White; a red variant exists (SL_36) |
| white_rice | partial | SL_6 Rice, White Nadu, Boiled | Rice, White Nadu, Boiled; other white rice varieties give nearly the same values |
| asmi | none | — | no match in the allowed tables (only a regional-table sweet exists) |
| brinjal_dish | none | — | no cooked brinjal dish; only raw eggplant (USDA) and Brinjal Curry (SL_72, a different dish) |
| cutlet | none | — | no match in the allowed tables |
| dhal_curry | exact | SL_54 Dhal Curry, Thick | owner choice 2026-10-18; the watery (SL_55) and spinach (SL_56) versions differ a lot |
| fish_curry | close | SL_146 Chili Fish Curry | owner choice 2026-10-18; white or dry fish curries differ |
| kokis | none | — | no match in the allowed tables |
| konda_kewum | none | — | no match in the allowed tables |
| lunu_miris | none | — | no lunu miris row; Coconut Sambol is a different recipe |
| meat_curry | close | SL_158 Chicken Curry | owner choice 2026-10-18; beef and other meat curries differ |
| milkshake | close | US_170884 Milk shakes, thick vanilla (USDA SR Legacy) | owner choice 2026-10-18; other flavours differ |
| mun_kewum | none | — | no match in the allowed tables |
| noodles | partial | SL_33 Boiled Noodles | owner choice 2026-10-18; fried noodles have more fat. SL_32 Fried Noodles is never used (same numbers as Carrot Curry, SL_74) |
| pappadam | none | — | no match in the allowed tables |
| patty | partial | US_167660 Beef empanada (USDA SR Legacy) | owner choice 2026-10-18; a Sri Lankan patty differs |
| shrimp_curry | none | — | no match (the Prawn Curry row was excluded for inconsistent values) |
| submarine | partial | US_170309 Submarine sandwich, oven roasted chicken (USDA SR Legacy) | owner choice 2026-10-18; other fillings differ |
| watalappam | none | — | no match in the allowed tables |

48 classes reviewed: 16 exact, 7 close, 15 partial, 10 none.

The three USDA rows (`US_170884`, `US_170309`, `US_167660`) come from USDA SR Legacy (read from the local FoodData Central download, per 100 g). Available carbohydrate is the USDA "by difference" total minus fibre, as for the Foundation rows; there is no sugars value. They are in `data/c1/c1_foods_combined.csv` with source `USDA FoodData Central, SR Legacy` (backup `c1_foods_combined.before_srlegacy_2026-10-18.csv`, both outside git).
