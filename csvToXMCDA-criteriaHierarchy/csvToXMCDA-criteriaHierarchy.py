# -*-coding:utf-8 -*


'''
DIVIZ

python script -i infile1 -c outfile1 -C outfile2 -m outfile3
1 x infile
3 x outfile

Transforms a file containing criteria values from a comma-separated values (CSV) file to two XMCDA compliant files, containing the corresponding criteria ids and their criteriaHierarchy.'''
import argparse, csv, sys, os
from optparse import OptionParser

sys.path.append('/Users/wachu/mgr/src')
     
import PyXMCDA


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
    PyXMCDA.writeHeader(outfile)
    outfile.write('  <criteria>\n')
    for id in criteria_ids:
        outfile.write('    <criterion id="%s" />\n' % id)
    outfile.write('  </criteria>\n')
    PyXMCDA.writeFooter(outfile)
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
    PyXMCDA.writeHeader(outfile)
    outfile.write('  <%s>' % mcdaConcept)
    outfile.write('''
    <description>
      <comment>A hierarchy of criteria</comment>
    </description>''')


    xmlparents = [ xml_value_label % v for v in criteria_ids ]


    outfile.write(make_tree('', parents, criteria_ids))
        
#    for id, weight in map(None, criteria_ids, xmlparents):
#        outfile.write("""
#    <criterionParent>
#      <criterionID>%s</criterionID>
#%s
#    </criterionParent>
#""" % (id, weight))
    outfile.write('\n  </%s>\n' % mcdaConcept)
    PyXMCDA.writeFooter(outfile)
    outfile.close()

def csv_to_criteriaValues(csv_file, out_criteria, out_criteriaValues):
    # If some mandatory input files are missing
    if not os.path.isfile(csv_file):
        raise ValueError, "input file 'criteriaHierarchy.csv' is missing: " + os.path.realpath(csv_file)
    criteria_ids, mcdaConcept, parents = transform(csv_file)
    output_criteria(out_criteria, criteria_ids)
    output_criteriaValues(out_criteriaValues, criteria_ids, mcdaConcept, parents)


def main(argv=None):
    if argv is None:
        argv = sys.argv
    
    parser = argparse.ArgumentParser(description=__doc__)

    grp_input = parser.add_mutually_exclusive_group(required=True)
    grp_input.add_argument('-I', '--in-dir')
    grp_input.add_argument('-i', '--csv')

    grp_output = parser.add_argument_group("Outputs",
                                           description="Options -c and -C are linked and should be supplied (or omitted) together.  They are mutually exclusive with option -O")
    grp_output.add_argument('-O', '--out-dir', metavar='<output directory>', help='If specified, the files "criteria.xml" and "criteriaValues.xml" will be created in this directory.  The directory must exist beforehand.')
    grp_output.add_argument('-c', '--criteria', metavar='output.xml')
    grp_output.add_argument('-C', '--criteriaValues', metavar='output.xml')

    grp_output.add_argument('-m', '--messages', metavar='<file.xml>', help='All messages are redirected to this XMCDA file instead of being sent to stdout or stderr.  Note that if an output directory is specified (option -O), the path is relative to this directory.')

    args = parser.parse_args()
    #in_dir = options.in_dir
    #out_dir = options.out_dir
    if args.out_dir and (args.criteria or args.criteriaValues):
        parser.error('Options -O and -c/-C are mutually exclusive')
    if args.criteria != args.criteriaValues \
        and None in (args.criteria, args.criteriaValues):
        parser.error('Options -c and -C must be supplied (or omitted) together')
    if args.out_dir and args.criteria:
        parser.error('Options -O and -c/-C are mutually exclusive')

    if args.in_dir:
        csv_file = os.path.join(args.in_dir, 'criteriaHierarchy.csv')
    else:
        csv_file = args.csv

    if args.out_dir:
        out_criteria = os.path.join(args.out_dir, 'criteria.xml')
        out_criteriaValues = os.path.join(args.out_dir, 'criteriaHierarchy.xml')
    else:
        out_criteria = args.criteria
        out_criteriaValues = args.criteriaValues

    if args.messages and args.out_dir is not None:
        args.messages = os.path.join(args.out_dir, args.messages)
    else:
        messages = args.messages
#    messages = 'messages.xml'
    if messages:
        messages_fd = open(messages, 'w')
        PyXMCDA.writeHeader(messages_fd)

    exitStatus = 0
    #sys.stdout.write('Nurkujemy ' + sys.argv[2])
    #print 'lol'
    
    
    
    # here, sys.argv[0] is 'script'
    #csv_file = sys.argv[1]
    #out_criteria = sys.argv[2]
    #out_criteriaValues = sys.argv[3]
    
    try:
        csv_to_criteriaValues(csv_file, out_criteria, out_criteriaValues)
    except ValueError as e:
        exitStatus = -1
        if messages:
            xmcda_write_method_messages(messages_fd, 'error', [e.message])
        else:
            sys.stderr.write(e.message)
    else:
       if messages: xmcda_write_method_messages(messages_fd, 'log', ['Execution ok'])
    finally:
        if messages:
            PyXMCDA.writeFooter(messages_fd)
            messages_fd.close()

    return exitStatus

if __name__ == "__main__":
    sys.exit(main())
