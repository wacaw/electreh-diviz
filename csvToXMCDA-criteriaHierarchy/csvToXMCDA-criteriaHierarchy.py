"""
csvToXMCDA - Transforms a file containing criteria values from a comma-separated values (CSV)
file to two XMCDA compliant files, containing the corresponding criteria ids and their criteriaHierarchy.
Usage:
    csvToXMCDA-criteriaHierarchy.py -i DIR -o DIR

Options:
    -i DIR     Specify input directory. It should contain the following files:
                   criteria_hierarchy.csv
    -o DIR     Specify output directory. Files generated as output:
                   criteria.xml
                   hierarchy.xml
    --version  Show version.
    -h --help  Show this screen.
"""

import argparse, csv, sys, os
from optparse import OptionParser
from docopt import docopt
import PyXMCDA as px
from common import comparisons_to_xmcda, create_messages_file, get_dirs, \
    get_error_message, get_input_data, get_linear, write_xmcda, Vividict
__version__ = '0.1.0'

def xmcda_write_method_messages(xmlfile, type, messages) :
    if type not in ('log', 'error'):
        raise ValueError, 'Invalid type: %s' % type
    xmlfile.write('<methodMessages>\n')
    for message in messages :
       xmlfile.write('<%sMessage><text><![CDATA[%s]]></text></%sMessage>\n' % (type, message, type))
    xmlfile.write('</methodMessages>\n')


def csv_reader(csv_file):
    csvfile = open(csv_file, "rb")
    dialect = csv.Sniffer().sniff(csvfile.read(1024))
    csvfile.seek(0)
    return csv.reader(csvfile, dialect)

def string_to_numeric_list(alist):
    """
    Check that the list is made of numeric values only.  If the values in the
    list are not valid numeric values, it also tries to interpret them with
    the comma character (",") as the decimal separator.  This may happen when
    the csv is exported by MS Excel on Windows platforms, where the csv format
    depends on the local settings.

    Note that we do not check whether the decimal separator is the same
    everywhere: a list containing "4.5" and "5,7" will be accepted.

    Return the list filled with the corresponding float values, or raise
    ValueError if at least one value could not be interpreted as a numeric
    value.
    """
    l = None
    try:
        l = [ float(i) for i in alist ]
    except ValueError:
        pass
    else:
        return l
    # try with ',' as a comma separator
    try:
        l = [ float(i.replace(',', '.')) for i in alist ]
    except ValueError:
        raise ValueError, "Invalid literal for float"
    else:
        return l

def transform(csv_file):
    try:
        content = csv_reader(csv_file)
    except:
        raise ValueError, 'Could not read csv file'

    try:
        children = content.next()
    except StopIteration:
        raise ValueError, 'Invalid csv file (is it empty?)'

    try:
        parents = content.next()
    except StopIteration:
        raise ValueError, 'Invalid csv file (second line is missing)'

    if parents[0] == 'parent' and (children[0] == 'children' or children[0] == 'child'):
        mcdaConcept = 'hierarchy'
    else:
        mcdaConcept = parents[0]
    children = children[1:]
    parents = parents[1:]

    #
    if not 'Root' in children:
        children=['Root']+children
        parents=['']+parents

    if len(children) == 0 or len(parents) == 0:
        raise ValueError, 'csv should contain at least one criteria/value'
    if len(children) != len(parents):
        raise ValueError, 'csv should contain the same number of criteria and values'
    return children, mcdaConcept, parents


def output_criteria(filename, criteria_ids):
    outfile = open(filename, 'w')
    px.writeHeader(outfile)
    outfile.write('  <criteria>\n')
    for id in criteria_ids:
        outfile.write('    <criterion id="%s" />\n' % id)
    outfile.write('  </criteria>\n')
    px.writeFooter(outfile)
    outfile.close()


xml_value_label = '''
        <criterionID>%s</criterionID>
      '''[1:]
def xml_node_label(a, b='', space=''):
    return '''
      %s<node>
        %s<criterionID>%s</criterionID>    %s%s
      %s</node>''' % (space, space, a, space, b, space)

def make_tree(root, parents, xmlparents, level=1, maxlevel=100):
    ret = ''
    space = '\t'
    if level > maxlevel:
        return ''
    for idx, parent in enumerate(parents):
        if parent == root:
            ret += xml_node_label(xmlparents[idx], make_tree(xmlparents[idx], parents, xmlparents, level + 1, maxlevel), level * space)
    return ret


def output_criteriaValues(filename, criteria_ids, mcdaConcept, parents):
    outfile = open(filename, 'w')
    px.writeHeader(outfile)
    outfile.write('  <%s>' % mcdaConcept)
    outfile.write('''
    <description>
      <comment>A hierarchy of criteria</comment>
    </description>''')


    xmlparents = [ xml_value_label % v for v in criteria_ids ]

    outfile.write(make_tree('', parents, criteria_ids))

    outfile.write('\n  </%s>\n' % mcdaConcept)
    px.writeFooter(outfile)
    outfile.close()

def csv_to_criteriaValues(csv_file, out_criteria, out_hierarchy):
    criteria_ids, mcdaConcept, parents = transform(csv_file)
    output_criteria(out_criteria, criteria_ids)
    output_criteriaValues(out_hierarchy, criteria_ids, mcdaConcept, parents)

def main(argv=None):
    try:
        args = docopt(__doc__, version=__version__)
        output_dir = None
        input_dir, output_dir = get_dirs(args)
        exitStatus = 0
        files = {}
        filenames = [
            'criteria_hierarchy.csv',
        ]

        for f in filenames:
            file_name = os.path.join(input_dir, f)
            if not os.path.isfile(file_name):
                raise RuntimeError("Problem with the input file: '{}'."
                                        .format(f))
            tree_name = os.path.splitext(f)[0]
            if 'classes' in tree_name:
                tree_name = tree_name.replace('classes', 'categories')
            files.update({tree_name: file_name})
        exitStatus = 0
        csv_to_criteriaValues(files['criteria_hierarchy'], os.path.join(output_dir,'criteria.xml'), os.path.join(output_dir,'hierarchy.xml'))
        create_messages_file(None, ('Everything OK.',), output_dir)

    except ValueError as e:
        exitStatus = -1
        create_messages_file((e.message), ('error.',), output_dir)
    return exitStatus

if __name__ == "__main__":
    sys.exit(main())
