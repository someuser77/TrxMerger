import sys, shutil, copy, os, ntpath
import dateutil.parser
import xml.etree.ElementTree as ElementTree

unit_test_result_path_prefixed = "p:Results/p:UnitTestResult"
unit_test_path_prefixed = "p:TestDefinitions/p:UnitTest"
run_deployment_root_prefixed = "p:TestSettings/p:Deployment[@runDeploymentRoot]"
result_file_prefixed = "p:ResultFiles/p:ResultFile[@path]"

namespaces = {'p': 'http://microsoft.com/schemas/VisualStudio/TeamTest/2010'}
ElementTree.register_namespace("",namespaces['p'])

class Trx:
	def __init__(self, handle, path):
		self.root = ElementTree.parse(handle)
		self.handle = handle
		self.path = path
		self.dir = os.path.dirname(path)
	
	def __str__(self):
		return "Path: " + self.path + " BaseDir: " + self.dir

def get_deployment_dir(trx_root_element):
	return trx_root_element.find(run_deployment_root_prefixed, namespaces).attrib['runDeploymentRoot']

def set_deployment_dir(trx_root_element, value):
	deployment_root_node = trx_root_element.find(run_deployment_root_prefixed, namespaces)
	deployment_root_node.set('runDeploymentRoot', value)

def copy_result_files(source, target, execution_id):
	
	source_run_deployment_root = get_deployment_dir(source.root)
	target_run_deployment_root = get_deployment_dir(target.root)	
	
	result_file_path = unit_test_result_path_prefixed + "[@executionId='" + execution_id + "']/" + result_file_prefixed
	
	source_result_files = source.root.find(result_file_path, namespaces)
	
	if source_result_files is not None:
		
		source_result_files_dir = os.path.join(source.dir, source_run_deployment_root, "In", execution_id)
		target_result_files_dir = os.path.join(target.dir, target_run_deployment_root, "In", execution_id)
		
		shutil.copytree(source_result_files_dir, target_result_files_dir)

def load_and_merge(target_file, source_file):

	source = Trx(open(source_file), source_file)
	target = Trx(open(target_file, 'r+'), target_file)

	update_existing_test_results(source, target)

	append_new_tests(source, target)

	target.handle.seek(0)
	target.root.write(target.handle)
	target.handle.truncate()

	source.handle.close()
	target.handle.close()
		
def get_test_result_class_name(root, unit_test_result_node):
	class_name = root.find(unit_test_path_prefixed + "[@id='" + unit_test_result_node.attrib['testId'] + "']/p:TestMethod", namespaces).attrib['className'].split(',')[0]
	return class_name
	
def get_test_result_full_name(root, unit_test_result):
	class_name = get_test_result_class_name(root, unit_test_result)
	test_name = unit_test_result.attrib['testName']
	full_test_name = class_name + '.' + test_name
	return full_test_name
	
def find_test_result_by_full_name(root, full_test_name):
	i = full_test_name.rfind('.')
	class_name = full_test_name[:i]
	test_name = full_test_name[i+1:]
	xpath = unit_test_result_path_prefixed + "[@testName='" + test_name + "']"
	for test_result in root.iterfind(xpath, namespaces):
		if get_test_result_class_name(root, test_result) == class_name:
			return test_result

	return None

def update_existing_test_results(source, target):
	
	target_results = target.root.find("p:Results", namespaces)
	source_run_deployment_root = get_deployment_dir(source.root)
	target_run_deployment_root = get_deployment_dir(target.root)
	
	for source_unit_test_result in source.root.iterfind(unit_test_result_path_prefixed, namespaces):
		
		full_test_name = get_test_result_full_name(source.root, source_unit_test_result)
		
		target_unit_test_result = find_test_result_by_full_name(target.root, full_test_name)
		
		if target_unit_test_result is not None:
			
			source_start_time = dateutil.parser.parse(source_unit_test_result.attrib['startTime'])
			target_start_time = dateutil.parser.parse(target_unit_test_result.attrib['startTime'])
			
			if source_start_time > target_start_time:
				# source contains newer test result
				print "\tUpdating test result for: " + source_unit_test_result.attrib['testName']
				
				old_execution_id = target_unit_test_result.attrib['executionId']
				new_execution_id = source_unit_test_result.attrib['executionId']
				
				unit_test_execution = target.root.find(unit_test_path_prefixed + "/p:Execution[@id='" + old_execution_id + "']", namespaces) 
				unit_test_execution.set('id', new_execution_id)
				
				source_result_files = source_unit_test_result.find(result_file_prefixed, namespaces)
				
				if source_result_files is not None:
					
					old_result_files_dir = os.path.join(target.dir, target_run_deployment_root, "In", old_execution_id)
					
					if os.path.exists(old_result_files_dir):
						shutil.rmtree(old_result_files_dir)
				
					copy_result_files(source, target, new_execution_id)
				
				target_results.remove(target_unit_test_result)
				target_results.append(copy.deepcopy(source_unit_test_result))

def append_new_tests(source, target):
	
	target_test_definitions = target.root.find("p:TestDefinitions", namespaces)
	
	for source_unit_test in source.root.iterfind(unit_test_path_prefixed, namespaces):
		test_name = source_unit_test.attrib['name']
		test_class = source_unit_test.find('p:TestMethod', namespaces).attrib['className']
		xpath = unit_test_path_prefixed + "[@name='" + test_name + "']/p:TestMethod[@className='" + test_class + "']"
		target_unit_test = target.root.find(xpath, namespaces) 
		if target_unit_test is None:
			print "\tAdding test definition: " + source_unit_test.attrib['name']
			target_test_definitions.append(copy.deepcopy(source_unit_test))
			
	target_results = target.root.find("p:Results", namespaces)
	
	for source_test_result in source.root.iterfind(unit_test_result_path_prefixed, namespaces):
		full_test_name = get_test_result_full_name(source.root, source_test_result)
		target_test_result = find_test_result_by_full_name(target.root, full_test_name)
		if target_test_result is None:
			print "\tAdding test result: " + source_test_result.attrib['testName']
			target_results.append(copy.deepcopy(source_test_result))
			
			copy_result_files(source, target, source_test_result.attrib['executionId'])
					

def copy_base_trx(source, output):
	shutil.copyfile(source, output)
	source_deployment_dir = get_deployment_dir(ElementTree.parse(source))
	source_data_dir = os.path.abspath(os.path.join(os.path.dirname(source), source_deployment_dir))
	
	path, filename = os.path.split(output)
	filename = os.path.splitext(filename)[0]
	
	target_data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(output)), filename))
	
	if (source_data_dir == target_data_dir):
		return
	
	if (os.path.exists(target_data_dir)):
		shutil.rmtree(target_data_dir)
		
	if (os.path.exists(source_data_dir)):
		print "copying trx data dir from '" + source_data_dir + "' to '" + target_data_dir + "'"
		shutil.copytree(source_data_dir, target_data_dir)
		
	root = ElementTree.parse(output)
	set_deployment_dir(root, target_data_dir)
	root.write(output)
		
	

def rebuild_test_list(trx):
	test_entries = trx.find("p:TestEntries", namespaces)
	
	for test_entry in test_entries.findall("p:TestEntry", namespaces):
		test_entries.remove(test_entry)
		
	test_list_id = trx.find("p:TestLists/p:TestList[@name='Results Not in a List']", namespaces).attrib['id']
	
	for unit_test_result in trx.iterfind("p:Results/p:UnitTestResult", namespaces):
		unit_test_result.set('testListId', test_list_id)
		
		test_entry = ElementTree.Element('TestEntry')
		test_entry.set('testId', unit_test_result.attrib['testId'])
		test_entry.set('executionId', unit_test_result.attrib['executionId'])
		test_entry.set('testListId', test_list_id)
		test_entry.tail = os.linesep + "    "
		
		test_entries.append(test_entry)	

def remove_result_summary(trx):
	result_summary = trx.find("p:ResultSummary", namespaces)
	if  (result_summary is not None):
		trx.getroot().remove(result_summary)
	
def post_process(output_file):
	with open(output_file, 'r+') as trx_handle:
		 
		trx = ElementTree.parse(trx_handle)
		
		rebuild_test_list(trx)
		
		remove_result_summary(trx)
		
		trx_handle.seek(0)
		trx.write(trx_handle)
		trx_handle.truncate()

def merge(files):

	if len(files) < 2:
	  print 'Must specify at least one input file and an output file'
	  return
	  
	output = files[-1]
	first = files[0]
	print "Processing file: " + first

	copy_base_trx(first, output)

	files_to_process = files[1:-1]

	for file in files_to_process:
		print "Processing file: " + file
		load_and_merge(output, file)

	post_process(output)

if __name__ == '__main__':
	merge(sys.argv[1:])