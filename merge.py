import sys, shutil, copy, os, ntpath
import dateutil.parser
import xml.etree.ElementTree as ElementTree

unit_test_result_path_prefixed = "p:Results/p:UnitTestResult"
unit_test_path_prefixed = "p:TestDefinitions/p:UnitTest"
run_deployment_root_prefixed = "p:TestSettings/p:Deployment[@runDeploymentRoot]"

namespaces = {'p': 'http://microsoft.com/schemas/VisualStudio/TeamTest/2010'}
ElementTree.register_namespace("",namespaces['p'])

def get_deployment_dir(trx):
	return trx.find(run_deployment_root_prefixed, namespaces).attrib['runDeploymentRoot']

def set_deployment_dir(trx, value):
	deployment_root_node = trx.find(run_deployment_root_prefixed, namespaces).attrib['runDeploymentRoot']
	deployment_root_node.set('runDeploymentRoot', value)

def merge(target_file, source_file):

	source_file_base_dir = os.path.dirname(source_file)
	target_file_base_dir = os.path.dirname(target_file)
	
	source_file = open(source_file)
	target_file = open(target_file, 'r+')

	source = ElementTree.parse(source_file)
	target = ElementTree.parse(target_file)

	update_existing_test_results(source, target, source_file_base_dir, target_file_base_dir)

	append_new_tests(source, target)

	target_file.seek(0)
	target.write(target_file)
	target_file.truncate()

	source_file.close()
	target_file.close()

def update_existing_test_results(source, target, source_file_base_dir, target_file_base_dir):
	target_results = target.find("p:Results", namespaces)
	source_run_deployment_root = get_deployment_dir(source)
	target_run_deployment_root = get_deployment_dir(target)
	
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
				
				source_result_files = source_unit_test_result.find("p:ResultFiles/p:ResultFile[@path]", namespaces)
				if source_result_files is not None:
					#for result_file in source_result_files:
						# windows_path_parts = ntpath.split(result_file.attrib['path'])
						# path = os.path.join(windows_path_parts[0], windows_path_parts[1])
						
					source_result_files_dir = os.path.join(source_file_base_dir, source_run_deployment_root, "In", new_execution_id)
					target_result_files_dir = os.path.join(target_file_base_dir, target_run_deployment_root, "In", new_execution_id)
					
					old_result_files_dir = os.path.join(target_file_base_dir, target_run_deployment_root, "In", old_execution_id)
					
					if os.path.exists(old_result_files_dir):
						shutil.rmtree(old_result_files_dir)
						
					shutil.copytree(source_result_files_dir, target_result_files_dir)
				
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

def copy_base_trx(source, output):
	shutil.copyfile(source, output)
	source_deployment_dir = get_deployment_dir(ElementTree.parse(source))
	source_data_dir = os.path.join(os.path.dirname(source), source_deployment_dir)
	target_data_dir = os.path.join(os.path.abspath(os.path.dirname(output)), source_deployment_dir)
	print "copying trx data dir from '" + source_data_dir + "' to '" + target_data_dir + "'"
	if os.path.isdir(target_data_dir):
		shutil.rmtree(target_data_dir)
	shutil.copytree(source_data_dir, target_data_dir)

def rebuild_test_list(output_file):
	print "rebuild_test_list" 

files = sys.argv

if len(files) < 3:
  print 'Must specify at least one input file and an output file'
  exit()
  
output = files[-1]
print "Processing file: " + files[1]

copy_base_trx(files[1], output)

files_to_process = files[2:-1]

for file in files_to_process:
	print "Processing file: " + file
	merge(output, file)

rebuild_test_list(output)
  