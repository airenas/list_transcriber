############################################
-include Makefile.options
############################################
python_cmd=PYTHONPATH=./ LOG_LEVEL=INFO python
work_dir?=work
extr_dir?=out
n?=20
tr_url?=https://atpazinimas.intelektika.lt
############################################
${work_dir}/extracted: 
	mkdir -p $@
${work_dir}/trans:
	mkdir -p $@
############################################
info: 
	echo Data: ${data_in}
############################################
${work_dir}/extracted/.done: ${data_in} | ${work_dir}/extracted
	unzip ${data_in} -d ${work_dir}/extracted
	touch $@
############################################
${work_dir}/files.list: ${work_dir}/extracted/.done
	find ${extr_dir} -name "*.mp3" > $@	
############################################
${work_dir}/.done: ${work_dir}/files.list | ${work_dir}/trans
	$(python_cmd) src/predict.py --in_f $^ --out_dir ${work_dir}/trans --url $(tr_url) --workers ${workers} \
		--key ${key}
	touch $@
${work_dir}/trans.zip: ${work_dir}/.done
	cd ${work_dir} && zip -r trans.zip trans
############################################
build: ${work_dir}/trans.zip
############################################
clean:
	@echo -n "Drop $(work_dir)? Are you sure? [y/N] " && read ans && [ $${ans:-N} = y ]
	rm -rf $(work_dir)
.PHONY: clean

