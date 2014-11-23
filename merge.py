import sys, shutil, copy
import dateutil.parser
import xml.etree.ElementTree as ElementTree

unit_test_result_path_prefixed = "p:Results/p:UnitTestResult"
unit_test_path_prefixed = "p:TestDefinitions/p:UnitTest"

namespaces = {'p': 'http://microsoft.com/schemas/VisualStudio/TeamTest/2010'}
ElementTree.register_namespace("",namespaces['p'])

def merge(target_file, source_file):
	
	source_file = open(source_file)
	target_file = open(target_file, 'r+')

	source = ElementTree.parse(source_file)
	target = ElementTree.parse(target_file)

	update_existing_test_results(source, target)

	append_new_tests(source, target)

	target_file.seek(0)
	target.write(target_file)
	target_file.truncate()

	source_file.close()
	target_file.close()

def update_existing_test_results(source, target):
	target_results = target.find("p:Results", namespaces)
	
	for source_unit_test_result in source.iterfind(unit_test_result_path_prefixed, namespaces):
		target_unit_test_result = target.find(unit_test_result_path_prefixed + "[@testName='" + source_unit_test_result.attrib['testName'] + "']", namespaces) 
		if target_unit_test_result is not None:
			
			source_start_time = dateutil.parser.parse(source_unit_test_result.attrib['startTime'])
			target_start_time = dateutil.parser.parse(target_unit_test_result.attrib['startTime'])
			
			if source_start_time > target_start_time:
				# source contains newer test result
				print "\tUpdating test result for: " + source_unit_test_result.attrib['testName']
				
				old_execution_id = target_unit_test_result.attrib['executionId']
				new_execution_id = source_unit_test_result.attrib['executionId']
				
				unit_test_execution = target.find(unit_test_path_prefixed + "/p:Execution[@id='" + old_execution_id + "']", namespaces) 
				unit_test_execution.set('id', new_execution_id)
				
				target_results.remove(target_unit_test_result)
				target_results.append(copy.deepcopy(source_unit_test_result))

def append_new_tests(source, target):
	
	target_test_definitions = target.find("p:TestDefinitions", namespaces)
	
	for source_unit_test in source.iterfind(unit_test_path_prefixed, namespaces):
		target_unit_test = target.find(unit_test_path_prefixed + "[@name='" + source_unit_test.attrib['name'] + "']", namespaces) 
		if target_unit_test is None:
			print "\tAdding test definition: " + source_unit_test.attrib['name']
			target_test_definitions.append(copy.deepcopy(source_unit_test))
			
	target_results = target.find("p:Results", namespaces)
	
	for source_test_result in source.iterfind(unit_test_result_path_prefixed, namespaces):
		target_test_result = target.find(unit_test_result_path_prefixed + "[@testName='" + source_test_result.attrib['testName'] + "']", namespaces) 
		if target_test_result is None:
			print "\tAdding test result: " + source_test_result.attrib['testName']
			target_results.append(copy.deepcopy(source_test_result))

files = sys.argv



if len(files) < 3:
  print 'Must specify at least one input file and an output file'
  exit()
  
output = files[-1]
print "Processing file: " + files[1]
shutil.copyfile(files[1], output)

files_to_process = files[2:-1]

for file in files_to_process:
	print "Processing file: " + file
	merge(output, file)

  