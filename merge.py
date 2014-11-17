import sys, shutil
import copy
import xml.etree.ElementTree as ElementTree

namespaces = {'p': 'http://microsoft.com/schemas/VisualStudio/TeamTest/2010'}

def merge(target_file, source_file):
	
	source_file = open(source_file)
	target_file = open(target_file, 'r+')

	source = ElementTree.parse(source_file)
	target = ElementTree.parse(target_file)

	append_new_tests(source, target)

	target_file.seek(0)
	target.write(target_file)
	target_file.truncate()

	source_file.close()
	target_file.close()

def append_new_tests(source, target):
	
	target_test_definitions = target.find("p:TestDefinitions", namespaces)
	
	for element in source.iterfind("p:TestDefinitions/p:UnitTest", namespaces):
		node = target.find("p:TestDefinitions/p:UnitTest[@name='" + element.attrib['name'] + "']", namespaces) 
		if node == None:
			print "Adding test definition: " + element.attrib['name']
			target_test_definitions.append(copy.deepcopy(element))
			
	target_results = target.find("p:Results", namespaces)
	
	for element in source.iterfind("p:Results/p:UnitTestResult", namespaces):
		node = target.find("p:Results/p:UnitTestResult[@testName='" + element.attrib['testName'] + "']", namespaces) 
		if node == None:
			print "Adding test result: " + element.attrib['testName']
			target_results.append(copy.deepcopy(element))

files = sys.argv

ElementTree.register_namespace("","http://microsoft.com/schemas/VisualStudio/TeamTest/2010")

if len(files) < 3:
  print 'Must specify at least one input file and an output file'
  exit()
  
output = files[-1]

shutil.copyfile(files[1], output)

merge(output, files[2])

  