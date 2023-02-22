
function Deidentifierfile(originalPlanPath, Copy_dir, value, valuename)

%variables
global KIM


% Button pushed function: SelectKIMTrajFolderButton
 %       function SelectKIMTrajFolderButtonPushed(app, event)
  %          global KIM
   %         folder_name = uigetdir('C:\');     
    %        KIM.KIMTrajFolder=folder_name;
     
     %   end

% Button pushed function: Button
     %   function ButtonPushed(app, event)
            %global KIM
    %        %KIM.handles=handles;
   %         dynamicTest_chandrima_test1(KIM.KIMRobotFile, KIM.KIMTrajFolder, KIM.KIMcoordFile, KIM.KIMparamFile)
  %      end
%Input
Firstname = 'Robinson'
Lastname = 'Raymond'
%originalPlanPath = strcat ('C:\Users\csen4522\OneDrive - The University of Sydney (Staff)\Desktop\New folder (3)\Robinson,Raymond_1723198\');
%originalPlanPath = KIM.originalPlanPath
%Copy_dir = strcat ('C:\Users\csen4522\OneDrive - The University of Sydney (Staff)\Desktop\New folder (3)\Test4\');
%Copy_dir = KIM.Copy_dir
new = value;


% Valid for all files 
%old = strcat(Firstname, ',', Lastname);
old = valuename;

% Output
%mkdir (Copy_dir,'KIM-KV\') 
tic
copyfile (originalPlanPath , Copy_dir)
toc

%% Reading trajectory files with Gantry angles
kVFolder = strcat(Copy_dir,'\KIM-KV\')

cd(kVFolder)
list = ls([kVFolder '\MarkerLocationsGA*.txt']);
noOfOLTrajFiles = size(list,1);
for n = 1:noOfOLTrajFiles
        fid=fopen([kVFolder '\MarkerLocationsGA_CouchShift_' num2str(n-1) '.txt']); 
        f=fread(fid,'*char')';
        fclose(fid);
        
        f = regexprep(f,old,new);
        
        fid  = fopen([kVFolder '\MarkerLocationsGA_CouchShift_' num2str(n-1) '.txt'],'w');
        fprintf(fid,'%s',f);
        fclose(fid);
end

%% Reading trajectory files without Gantry angles
list = ls([kVFolder '\MarkerLocations_*.txt']);
noOfOLTrajFiles = size(list,1);
for n = 1:noOfOLTrajFiles
        fid=fopen([kVFolder '\MarkerLocations_CouchShift_' num2str(n-1) '.txt']); 
        f=fread(fid,'*char')';
        fclose(fid);
        
        f = regexprep(f,old,new);
        
        fid  = fopen([kVFolder '\MarkerLocations_CouchShift_' num2str(n-1) '.txt'],'w');
        fprintf(fid,'%s',f);
        fclose(fid);
end

% Changing acquisition logs
cd(Copy_dir)

fid=fopen([Copy_dir '\acquisition.log']); 
f=fread(fid,'*char')';
fclose(fid);
f = regexprep(f,old,new);
fid  = fopen([Copy_dir '\acquisition.log'],'w');
fprintf(fid,'%s',f);
fclose(fid);
