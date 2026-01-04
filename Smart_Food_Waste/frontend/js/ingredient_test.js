// Lightweight test runner for IngredientUtils (not required by page, helper if needed)
(function(){
  if (typeof window === 'undefined' || !window.IngredientUtils) return;
  const samples = [
    'to 1 1/2 cups coriander leaves',
    '½ teaspoon cumin seeds (jeera)',
    'hot green chilies ((adjust to taste))',
    '((peeled)) 2 cloves garlic',
    'to 2 teaspoons Lemon juice ((adjust to taste))',
    '1/4 teaspoon Salt ((adjust to taste))',
    'to 8 garlic cloves',
    'to 10 dried red chilies ((Byadgi or Kashmiri or any less spicy kind))',
    'tablespoon peanuts ((optional))',
    'medium potatoes ((aloo – 2 ¼ cups crumbled))'
  ];

  const results = samples.map(s=> ({ input: s, parsed: window.IngredientUtils.parseIngredient(s) }));
  console.log('IngredientUtils test results:', results);
})();
