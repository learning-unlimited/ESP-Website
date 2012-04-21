import os
import os.path
import tempfile

from esp import settings

def test_js_compile(display=False):

    #   Determine if the Closure compiler is installed and give up if it isn't
    if hasattr(settings, 'CLOSURE_COMPILER_PATH'):
        closure_path = settings.CLOSURE_COMPILER_PATH.rstrip('/') + '/'
    else:
        closure_path = ''
    if not os.path.exists('%scompiler.jar' % closure_path):
        print 'Closure compiler not found.  Checked CLOSURE_COMPILER_PATH ="%s"' % closure_path
        return
        
    closure_output_code = tempfile.gettempdir() + '/closure_output.js'
    closure_output_file = tempfile.gettempdir() + 'closure.out'
    
    base_path = settings.MEDIA_ROOT + 'scripts/'
    exclude_names = ['yui', 'extjs', 'jquery', 'showdown']
    
    #   Walk the directory tree and try compiling
    path_gen = os.walk(base_path)
    num_files = 0
    file_list = []
    
    for path_tup in path_gen:
        dirpath = path_tup[0]
        dirnames = path_tup[1]
        filenames = path_tup[2]
        exclude = False
        for name in exclude_names:
            if name in dirpath:
                exclude = True
                break
        if not exclude:
            if display:
                print 'Entering directory %s' % dirpath
            for file in filenames:
                if not file.endswith('.js'):
                    continue
                exclude = False
                for name in exclude_names:
                    if name in file:
                        exclude = True
                        break
                if exclude:
                    continue
                
                file_list.append('%s/%s' % (dirpath, file))
                num_files += 1
                
    file_args = ' '.join([('--js %s' % file) for file in file_list])
    os.system('java -jar %s/compiler.jar %s --js_output_file %s 2> %s' % (closure_path, file_args, closure_output_code, closure_output_file))
    checkfile = open(closure_output_file)
    results = [line.strip() for line in checkfile.readlines() if len(line.strip()) > 0]

    if len(results) > 0:
        if display:
            print '-- Found errors'
            for err in results: print err.strip()
    else:
        if display:
            print '-- Clean'
            
    checkfile.close()
                
    if display:
        print 'Checked %d files; %d had errors/warnings' % (num_files, len(results))
        
    return results
    
if __name__ == '__main__':
    closure_result = test_js_compile(display=True)
    print 'Result: %s' % closure_result
    
