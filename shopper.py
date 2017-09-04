#!python

"""
TODO list:
- [X] Generate list of base ingredients needed
    - [ ] Interface to provide certain ingredients you already have
- [ ] Generate a list of steps/intermediate products the user needs to make
"""


# TODO: convert the ingredient list input method to comma delimited items
# should have done that earlier but I wasn't thinking
# TODO: count should be a floating point number because not all crafts make just one
# TODO: track shards/crystals
# TODO: track wastage
# TODO: map profession to item and show

# TODO: Create some form of forward generator for ingredients

import yaml
import argparse
import pprint
import textwrap
from collections import namedtuple
import json


Ingredient = namedtuple('Ingredient', ['name', 'count'])

def parse_ingredient_input(input_string)-> list:
    """returns a list of (name, count) tuples
    raises ValueError if any count is not a natural number
    """
    input_list = input_string.strip().split()
    ingredient_list = []
    while input_list:
        elem = input_list.pop(0)

        if elem.isdigit():
            if int(elem) < 1:
                print('Count must be a natural number')
                raise ValueError()
            count = int(elem)
        else:
            # handle the first case
            count = 1

        elem = input_list.pop(0)

        # keep popping until we see a number
        tokens = [elem]
        while input_list and not input_list[0].isdigit():
            tokens.append(input_list.pop(0))
        name = ' '.join(tokens)

        ingredient_list.append((name, count))

    return ingredient_list


def input_yn(string)-> bool:
    string += ' (y/n): '
    while True:
        result = input(string)
        result = result.lower()
        if result != 'y' and result != 'n':
            continue
        else:
            break
    if result == 'y':
        return True
    else:
        return False


class RecipeDatabase(object):

    def __init__(self, data_file)-> None:
        self._database = {}
        if isinstance(data_file, str):
            data_file = open(data_file, 'r')
        for elem in yaml.load_all(data_file):
            self._database = {**self._database, **elem}

    def __getitem__(self, key)-> dict:
        return self._database[key]

    def __contains__(self, key)-> bool:
        return key in self._database

    def __iter__(self):
        return iter(self._database)

    def export(self, dest)-> None:
        if isinstance(dest, str):
            dest = open(dest, 'w')
        json.dump(self._database, dest, indent=4)
        print('Wrote to destination')

    def items(self):
        return self._database.items()

    def keys(self):
        return self._database.keys()

    def shop_recipe(self, key, count = 1):
        ingredients = self._list_ingredients(key)
        ret_ingredients = {k: v * int(count) for k, v in ingredients.items()}
        return ret_ingredients

    def _list_ingredients(self, item, ignore_list = [], basic_only = True)-> dict:
        """Given an item break it down into smaller components
        """
        if item not in self._database:
            print(item + ' not described in database, please define it')
            self.add_recipe(item)

        if self._database[item] is None: # basic type
            return {item : 1}

        shopping_list = dict(self._database[item])
        for k, v in self._database[item].items():
            components = {x : y * v
                          for x, y in self._list_ingredients(k, ignore_list,
                                                            basic_only = basic_only).items()}
            if basic_only is True:
                del shopping_list[k]

            for x, y in components.items():
                if x in shopping_list:
                    shopping_list[x] += y
                else:
                    shopping_list[x] = y

        return shopping_list

    def _collect_ingredients(self, recipe):
        print('Please key in a list of ingredients in the format <N> <Ingredient>')
        while True:
            ingredients = input('\tIngredient(s):')
            try:
                ingredient_tuples = parse_ingredient_input(ingredients)
                pprint.pprint(ingredient_tuples)
            except ValueError:
                continue
            else:
                return [Ingredient(x, y) for x, y in ingredient_tuples]

    def add_recipe(self, recipe = '')-> None:

        if recipe in self._database:
            print('Recipe already exists in database')
            return

        recipe = recipe.lower()

        basic = input_yn('Is [' + recipe + '] a complex recipe? (i.e, built on other ingredients)')
        if basic is False:
            self._database[recipe] = None
            return

        print('Defining ingredients for ' + recipe + ' :')

        ingredient_list = self._collect_ingredients(recipe)
        recipe_content = {}
        for ingredient, count in ingredient_list:
            # basic ingredients dont have a count
            if ingredient not in self._database:
                print('''An ingredient you defined is not listed in the database [''' + ingredient + ''']. Please define it''')
                self.add_recipe(ingredient)

            recipe_content[ingredient] = count

        self._database[recipe] = recipe_content

    def delete_recipe(self, recipe)-> None:
        raise NotImplementedError()

    def ingredient_distance(self, key)-> int:
        """Finds the number of longest chain of crafting you need before you can
        actually craft this ingredient. If there are multiple chains (common),
        take the longest one
        """
        if key not in self._database:
            raise KeyError()

        if self._database[key] is None:
            return 0

        distance = {}
        for k, v in self._database[key].items():
            distance[k] = self.ingredient_distance(k) + 1

        return max(v for k, v in distance.items())

    def order_recipe(self, recipe, count)-> list:
        """generates a list of things to build, starting from the base parts
        """
        if recipe not in self._database:
            raise KeyError()

        all_ingredients = {}
        for k, v in self._list_ingredients(recipe, basic_only = False).items():
            if self._database[k] is not None:
                all_ingredients[k] = v

        all_ingredients[recipe] = 1
        ingredient_distance = []
        for k, v in all_ingredients.items():
            ingredient_distance.append((k, v, self.ingredient_distance(k)))

        ingredient_distance.sort(key=lambda tup: tup[2])

        return [(x, y * int(count)) for x, y ,z in ingredient_distance]

    def rename_recipe(self, old, new):
        if old not in self._database:
            raise KeyError()
        for k, v in self._database.items():
            if v is not None:
                if old in v:
                    v[new] = v[old]
                    del v[old]
        self._database[new] = self._database[old]
        del self._database[old]


def format_shopping_list(ingredients, ordering = None)-> None:
    indenter = textwrap.TextWrapper(initial_indent='\t',
                                    subsequent_indent='\t')

    print('Get:')
    for k, v in ingredients.items():
        print(indenter.fill('{:>3} {}(s)'.format(v, k)))

    if ordering is None:
        return

    print('Craft:')
    for index, elem in enumerate(ordering):
        print(indenter.fill('{:>3}: {} {}(s)'.format(index, elem[1], elem[0])))


def parse_args():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--data',
        help='''
        yaml configuration file
        ''',
        action='store',
        type=str,
        default='./materials.json',
        dest='data'
    )

    subparsers = parser.add_subparsers(help='help for subcommands',
                                       dest='command')
    make_parser = subparsers.add_parser('make', help='help for make')

    make_parser.add_argument(
        '-n',
        '--count',
        help='''
        the amount of these items you're making
        ''',
        action='store',
        type=int,
        default=1,
    )

    make_parser.add_argument(
        'item',
        help='''
        the item to be made
        ''',
        action='store',
        nargs='*',
        type=str
    )

    add_recipe_parser = subparsers.add_parser('add', help='help for adding recipes')

    add_recipe_parser.add_argument(
        'item',
        help='''
        the item you want to add
        ''',
        action='store',
        type=str
    )

    delete_recipe_parser = subparsers.add_parser('del', help='help for deleting recipes')

    delete_recipe_parser.add_argument(
        'item',
        help='''
        the item you want to delete
        ''',
        action='store',
        type=str
    )

    rename_recipe_parser = subparsers.add_parser('rename', help='help for renaming recipes')

    rename_recipe_parser.add_argument(
        'old',
        help='''
        the item you want to rename from
        ''',
        action='store',
        type=str
    )

    rename_recipe_parser.add_argument(
        'new',
        help='''
        the item you want to rename to
        ''',
        action='store',
        type=str
    )

    return parser.parse_args()


def format_item_list(items)-> list:
    if len(items) == 1:
        return [(items[0], 1)]
    return zip(items[1::2], items[0::2])


def join_shop_recipes(recipes):
    """recipes is a list of dictionaries that shop_recipe returns
    """
    joined_recipes = {}
    for recipe in recipes:
        for k, v in recipe.items():
            if k not in joined_recipes:
                joined_recipes[k] = v
            else:
                joined_recipes[k] += v
    return joined_recipes

def join_order_recipes(database, ordered_recipes):
    joined_orders = {}
    for order in ordered_recipes:
        for k, v in order:
            if k not in joined_orders:
                joined_orders[k] = v
            else:
                joined_orders[k] += v

    joined_orders = [(k, v) for k, v in joined_orders.items()]
    joined_orders.sort(key=lambda tup: database.ingredient_distance(tup[0]))
    return joined_orders


def main()-> None:

    args = parse_args()

    database = RecipeDatabase(args.data)

    if args.command == 'make':
        ingredients = []
        ordering = []
        for item, count in format_item_list(args.item):
            ingredients.append(database.shop_recipe(item, count))
            ordering.append(database.order_recipe(item, count))
        ingredients = join_shop_recipes(ingredients)
        ordering = join_order_recipes(database, ordering)
        format_shopping_list(ingredients, ordering)
    elif args.command == 'add':
        database.add_recipe(recipe = args.item)
    elif args.command == 'rename':
        database.rename_recipe(old=args.old, new=args.new)

    database.export(args.data)

    # import json
    # with open('json.json', 'w') as jsonfile:
    #     json.dump(database._database, jsonfile, indent=4)


if __name__ == '__main__':
    main()
